(() => {
	"use strict";

	const loginPanel = document.querySelector("#login-panel");
	const managerPanel = document.querySelector("#manager-panel");
	const loginForm = document.querySelector("#login-form");
	const loginMessage = document.querySelector("#login-message");
	const shipmentForm = document.querySelector("#shipment-form");
	const shipmentMessage = document.querySelector("#shipment-message");
	const recordsMessage = document.querySelector("#records-message");
	const recordsList = document.querySelector("#records-list");
	const recordsSummary = document.querySelector("#records-summary");
	const recordsSearch = document.querySelector("#records-search");
	const statusFilter = document.querySelector("#records-status-filter");
	const recordsSort = document.querySelector("#records-sort");
	const saveButton = document.querySelector("#save-shipment-button");
	const cancelButton = document.querySelector("#cancel-edit-button");
	let busy = false;
	let records = [];

	function escapeHtml(value) {
		return String(value ?? "").replace(
			/[&<>"']/g,
			(character) =>
				({
					"&": "&amp;",
					"<": "&lt;",
					">": "&gt;",
					'"': "&quot;",
					"'": "&#39;",
				})[character],
		);
	}

	function showMessage(element, message) {
		element.textContent = message;
		element.hidden = !message;
	}

	function friendlyError(error, fallback) {
		if (error.kind === "network" || error.kind === "server")
			return "The service is temporarily unavailable. Please try again shortly.";
		if (error.kind === "validation") return "Please check the information and try again.";
		if (error.kind === "unauthorized") return "Your session has expired. Please sign in again.";
		return fallback;
	}

	function recordId(record) {
		return (
			record.id ??
			record.shipment_id ??
			record.shipmentId ??
			record.tracking_id ??
			record.trackingId ??
			""
		);
	}

	function recordStatus(record) {
		return record.current_status ?? record.currentStatus ?? record.status ?? "Status unavailable";
	}

	function recordLocation(record) {
		return record.location ?? "";
	}

	function recordDescription(record) {
		return record.status_description ?? record.statusDescription ?? record.description ?? "";
	}

	function recordUpdatedAt(record) {
		return record.updated_at ?? record.updatedAt ?? "";
	}

	function formatDate(value) {
		if (!value) return "Not available";
		const date = new Date(value);
		if (Number.isNaN(date.getTime())) return String(value);
		return new Intl.DateTimeFormat(undefined, {
			day: "numeric",
			month: "short",
			year: "numeric",
			hour: "numeric",
			minute: "2-digit",
		}).format(date);
	}

	function visibleRecords() {
		const query = recordsSearch.value.trim().toLocaleLowerCase();
		const selectedStatus = statusFilter.value;
		const filtered = records.filter((record) => {
			const status = recordStatus(record);
			if (selectedStatus && status !== selectedStatus) return false;
			const searchableText = [
				record.tracking_id ?? record.trackingId ?? "",
				status,
				recordLocation(record),
				recordDescription(record),
			].join(" ").toLocaleLowerCase();
			return !query || searchableText.includes(query);
		});

		const sort = recordsSort.value;
		filtered.sort((left, right) => {
			if (sort === "tracking-asc") {
				return String(left.tracking_id ?? left.trackingId ?? "").localeCompare(
					String(right.tracking_id ?? right.trackingId ?? ""),
					undefined,
					{ numeric: true, sensitivity: "base" },
				);
			}
			if (sort === "status-asc") {
				return recordStatus(left).localeCompare(recordStatus(right), undefined, {
					sensitivity: "base",
				});
			}
			const leftTime = Date.parse(recordUpdatedAt(left)) || 0;
			const rightTime = Date.parse(recordUpdatedAt(right)) || 0;
			return sort === "updated-asc" ? leftTime - rightTime : rightTime - leftTime;
		});
		return filtered;
	}

	function renderRecords() {
		const visible = visibleRecords();
		recordsSummary.textContent = `${visible.length} of ${records.length} shipments`;
		if (!records.length) {
			recordsList.innerHTML = '<p class="records-empty">No shipment records yet.</p>';
			return;
		}
		if (!visible.length) {
			recordsList.innerHTML = '<p class="records-empty">No shipments match those filters.</p>';
			return;
		}
		recordsList.innerHTML = `<table class="records-table">
			<caption class="visually-hidden">Shipment records</caption>
			<thead><tr><th scope="col">Tracking ID</th><th scope="col">Status</th><th scope="col">Location</th><th scope="col">Last updated</th><th scope="col">Actions</th></tr></thead>
			<tbody>${visible
			.map((record) => {
				const id = recordId(record);
				const trackingId = record.tracking_id ?? record.trackingId ?? "Tracking ID unavailable";
				const status = recordStatus(record);
				const location = recordLocation(record);
				const description = recordDescription(record);
				const updatedAt = recordUpdatedAt(record);
				return `<tr>
					<td data-label="Tracking ID"><span class="record-id">${escapeHtml(trackingId)}</span></td>
					<td data-label="Status"><span class="record-status">${escapeHtml(status)}</span>${description ? `<span class="record-description">${escapeHtml(description)}</span>` : ""}</td>
					<td data-label="Location">${location ? escapeHtml(location) : "Not provided"}</td>
					<td data-label="Last updated">${escapeHtml(formatDate(updatedAt))}</td>
					<td class="record-actions-cell" data-label="Actions"><div class="record-actions"><button type="button" data-action="edit" data-id="${escapeHtml(id)}" aria-label="Edit ${escapeHtml(trackingId)}">Edit</button><button type="button" data-action="delete" data-id="${escapeHtml(id)}" aria-label="Delete ${escapeHtml(trackingId)}">Delete</button></div></td>
				</tr>`;
			})
			.join("")}</tbody>
		</table>`;
	}

	async function refreshRecords() {
		showMessage(recordsMessage, "");
		recordsList.innerHTML = '<p class="record-description" role="status">Loading shipments...</p>';
		try {
			records = await window.CourierApi.listShipments();
			renderRecords();
			return true;
		} catch (error) {
			if (error.kind === "unauthorized") {
				showLogin("Your session has expired. Please sign in again.");
			} else {
				recordsList.replaceChildren();
				showMessage(recordsMessage, friendlyError(error, "Unable to load shipment records."));
			}
			return false;
		}
	}

	function resetShipmentForm() {
		shipmentForm.reset();
		document.querySelector("#shipment-record-id").value = "";
		saveButton.textContent = "Save shipment";
		cancelButton.hidden = true;
		showMessage(shipmentMessage, "");
	}

	function showLogin(message = "") {
		managerPanel.hidden = true;
		loginPanel.hidden = false;
		loginForm.reset();
		showMessage(loginMessage, message);
	}

	function showManager() {
		loginPanel.hidden = true;
		managerPanel.hidden = false;
	}

	loginForm.addEventListener("submit", async (event) => {
		event.preventDefault();
		if (busy) return;
		const formData = new FormData(loginForm);
		const username = String(formData.get("username") || "").trim();
		const password = String(formData.get("password") || "");
		if (!username || !password) {
			showMessage(loginMessage, "Enter your username and password.");
			return;
		}

		busy = true;
		const button = loginForm.querySelector("[type='submit']");
		button.disabled = true;
		showMessage(loginMessage, "");
		try {
			await window.CourierApi.login({ username, password });
			loginForm.reset();
			if (!(await refreshRecords())) return;
			showManager();
		} catch (error) {
			showLogin(
				error.kind === "unauthorized"
					? "Your sign-in session could not be established. Please try again."
					: friendlyError(error, "Unable to load shipment records."),
			);
		} finally {
			busy = false;
			button.disabled = false;
		}
	});

	shipmentForm.addEventListener("submit", async (event) => {
		event.preventDefault();
		if (busy) return;
		const formData = new FormData(shipmentForm);
		const trackingId = String(formData.get("tracking_id") || "").trim();
		const status = String(formData.get("status") || "");
		if (!trackingId || !status) {
			showMessage(shipmentMessage, "Enter a tracking ID and select a status.");
			return;
		}

		const id = String(formData.get("record_id") || "");
		const record = {
			tracking_id: trackingId,
			status,
			location: String(formData.get("location") || "").trim(),
			description: String(formData.get("description") || "").trim(),
		};
		busy = true;
		saveButton.disabled = true;
		showMessage(shipmentMessage, "");
		try {
			await window.CourierApi.saveShipment(record, id);
			resetShipmentForm();
			await refreshRecords();
		} catch (error) {
			showMessage(shipmentMessage, friendlyError(error, "Unable to save this shipment."));
		} finally {
			busy = false;
			saveButton.disabled = false;
		}
	});

	recordsList.addEventListener("click", async (event) => {
		const button = event.target.closest("button[data-action]");
		if (!button || busy) return;
		const id = button.dataset.id;
		const record = records.find((item) => String(recordId(item)) === id);
		if (!record) return;

		if (button.dataset.action === "edit") {
			document.querySelector("#shipment-record-id").value = id;
			document.querySelector("#shipment-tracking-id").value =
				record.tracking_id ?? record.trackingId ?? "";
			document.querySelector("#shipment-status").value =
				record.current_status ?? record.currentStatus ?? record.status ?? "";
			document.querySelector("#shipment-location").value = record.location ?? "";
			document.querySelector("#shipment-description").value =
				record.status_description ?? record.statusDescription ?? record.description ?? "";
			saveButton.textContent = "Update shipment";
			cancelButton.hidden = false;
			document.querySelector("#shipment-tracking-id").focus();
			return;
		}

		if (
			button.dataset.action === "delete" &&
			window.confirm("Delete this shipment record? This cannot be undone.")
		) {
			busy = true;
			button.disabled = true;
			try {
				await window.CourierApi.deleteShipment(id);
				await refreshRecords();
			} catch (error) {
				showMessage(recordsMessage, friendlyError(error, "Unable to delete this shipment."));
			} finally {
				busy = false;
			}
		}
	});

	recordsSearch.addEventListener("input", renderRecords);
	statusFilter.addEventListener("change", renderRecords);
	recordsSort.addEventListener("change", renderRecords);
	cancelButton.addEventListener("click", resetShipmentForm);
	document.querySelector("#refresh-button").addEventListener("click", refreshRecords);
	document.querySelector("#logout-button").addEventListener("click", async (event) => {
		if (busy) return;
		busy = true;
		event.currentTarget.disabled = true;
		try {
			await window.CourierApi.logout();
		} catch {
			// The local admin view is cleared even if the server session has expired.
		} finally {
			managerPanel.hidden = true;
			loginPanel.hidden = false;
			loginForm.reset();
			records = [];
			recordsList.replaceChildren();
			showMessage(loginMessage, "");
			busy = false;
			event.currentTarget.disabled = false;
		}
	});

	async function restoreSession() {
		showLogin();
		try {
			await window.CourierApi.currentAdmin();
			if (!(await refreshRecords())) return;
			showManager();
		} catch (error) {
			if (error.kind !== "unauthorized")
				showMessage(loginMessage, friendlyError(error, "Unable to restore your session."));
		}
	}

	void restoreSession();
})();
