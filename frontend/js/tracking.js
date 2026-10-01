(() => {
	"use strict";

	const form = document.querySelector("#tracking-form");
	const input = document.querySelector("#tracking-id");
	const submitButton = form.querySelector("[type='submit']");
	const errorMessage = document.querySelector("#tracking-error");
	const loadingMessage = document.querySelector("#tracking-loading");
	const resultRegion = document.querySelector("#tracking-result");
	let isLoading = false;

	const statusCopy = {
		booked: ["Booked", "neutral", "Your shipment has been booked."],
		"picked up": ["Picked up", "info", "Your parcel has been picked up."],
		"in transit": ["In transit", "info", "Your parcel is currently in transit."],
		"out for delivery": ["Out for delivery", "info", "Your parcel is out for delivery."],
		delivered: ["Delivered", "success", "Your parcel has been delivered."],
		exception: ["Exception", "warning", "There is an update about your shipment."],
	};

	function escapeHtml(value) {
		return String(value).replace(
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

	function formatDate(value) {
		if (!value) return "";
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

	function statusInfo(status) {
		const normalized = String(status || "")
			.trim()
			.toLowerCase();
		const known = statusCopy[normalized];
		if (known) return { label: known[0], tone: known[1], description: known[2] };
		return {
			label: status ? String(status).replace(/[_-]+/g, " ") : "Status unavailable",
			tone: "neutral",
			description: "",
		};
	}

	function showError(title, message, kind = "error") {
		resultRegion.innerHTML = `<article class="state-message" data-state="${kind}" aria-labelledby="result-state-title"><h2 id="result-state-title">${escapeHtml(title)}</h2><p>${escapeHtml(message)}</p><button class="retry-button" type="button" data-action="retry">Try again</button></article>`;
		resultRegion.hidden = false;
	}

	function renderTimeline(history, currentStatus) {
		if (!history.length) return "";
		const latestStatus = String(currentStatus).trim().toLowerCase();
		const currentIndex = history.findIndex(
			(event) => String(event.status).trim().toLowerCase() === latestStatus,
		);
		const activeIndex = currentIndex >= 0 ? currentIndex : history.length - 1;
		const events = history
			.map((event, index) => {
				const title = event.status || event.description;
				const detail =
					event.status && event.description
						? `<p class="timeline-event-time">${escapeHtml(event.description)}</p>`
						: "";
				const time = formatDate(event.timestamp);
				const state =
					index < activeIndex ? "is-complete" : index === activeIndex ? "is-current" : "";
				return `<li class="timeline-event ${state}"><span class="timeline-dot" aria-hidden="true"></span><div><h4 class="timeline-event-title">${escapeHtml(title)}</h4>${detail}${time ? `<p class="timeline-event-time"><time datetime="${escapeHtml(event.timestamp)}">${escapeHtml(time)}</time></p>` : ""}</div></li>`;
			})
			.join("");
		return `<section class="timeline-wrap" aria-labelledby="timeline-title"><h3 class="timeline-title" id="timeline-title">Shipment progress</h3><ol class="timeline">${events}</ol></section>`;
	}

	function renderShipment(shipment, requestedId) {
		const trackingId = shipment.trackingId || requestedId;
		const status = statusInfo(shipment.status);
		const updated = formatDate(shipment.lastUpdated);
		const description = shipment.description || status.description || status.label;
		resultRegion.innerHTML = `<article class="result-card" aria-labelledby="shipment-status-heading">
			<div class="result-top">
				<div><p class="result-kicker">Tracking ID</p><p class="result-id">${escapeHtml(trackingId)}</p></div>
				<div class="status-block" data-tone="${status.tone}" aria-label="Current status: ${escapeHtml(status.label)}"><span class="status-symbol" aria-hidden="true"></span><div><h2 class="status-name" id="shipment-status-heading">${escapeHtml(status.label)}</h2><p class="status-description">${escapeHtml(description)}</p></div></div>
			</div>
			<dl class="result-meta"><div class="meta-item"><dt>Tracking ID</dt><dd>${escapeHtml(trackingId)}</dd></div><div class="meta-item"><dt>Current status</dt><dd>${escapeHtml(status.label)}</dd></div>${updated ? `<div class="meta-item"><dt>Last updated</dt><dd><time datetime="${escapeHtml(shipment.lastUpdated)}">${escapeHtml(updated)}</time></dd></div>` : ""}</dl>
			${renderTimeline(shipment.history, shipment.status)}
		</article>`;
		resultRegion.hidden = false;
	}

	async function submitTracking(event) {
		event.preventDefault();
		if (isLoading) return;

		const trackingId = input.value.trim();
		errorMessage.hidden = true;
		errorMessage.textContent = "";
		if (!trackingId) {
			errorMessage.textContent = "Enter your tracking ID to continue.";
			errorMessage.hidden = false;
			input.focus();
			return;
		}

		input.value = trackingId;
		isLoading = true;
		submitButton.disabled = true;
		submitButton.querySelector("span:first-child").textContent = "Checking shipment";
		loadingMessage.hidden = false;
		resultRegion.hidden = true;
		resultRegion.replaceChildren();

		try {
			const shipment = await window.CourierApi.trackShipment(trackingId);
			renderShipment(shipment, trackingId);
		} catch (error) {
			if (error.kind === "not-found") {
				showError(
					"Tracking ID not found",
					"We couldn't find a shipment with this tracking ID. Please check the ID and try again.",
					"not-found",
				);
			} else if (error.kind === "validation") {
				showError("Check your tracking ID", "Please check the ID and try again.");
			} else {
				showError("Unable to check your shipment right now", "Please try again in a moment.");
			}
		} finally {
			isLoading = false;
			submitButton.disabled = false;
			submitButton.querySelector("span:first-child").textContent = "Track shipment";
			loadingMessage.hidden = true;
		}
	}

	form.addEventListener("submit", submitTracking);
	resultRegion.addEventListener("click", (event) => {
		if (event.target.closest("[data-action='retry']")) {
			input.focus();
			document.querySelector("#tracking").scrollIntoView({ behavior: "smooth", block: "center" });
		}
	});
	document.querySelector("#copyright-year").textContent = String(new Date().getFullYear());
})();
