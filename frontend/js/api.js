(() => {
	"use strict";

	const settings = {
		baseUrl: "https://trackcourier-6hcj.onrender.com",
		paths: {
			tracking: "/api/tracking/{trackingId}",
			login: "/api/auth/login",
			logout: "/api/auth/logout",
			shipments: "/api/admin/shipments",
			shipment: "/api/admin/shipments/{id}",
		},
	};

	class ApiError extends Error {
		constructor(kind, message) {
			super(message);
			this.name = "ApiError";
			this.kind = kind;
		}
	}

	function endpoint(path) {
		return `${settings.baseUrl}${path}`;
	}

	async function request(path, options = {}) {
		let response;
		try {
			response = await fetch(endpoint(path), {
				...options,
				credentials: "include",
				headers: { Accept: "application/json", ...options.headers },
			});
		} catch {
			throw new ApiError("network", "The service could not be reached.");
		}

		const contentType = response.headers.get("content-type") || "";
		let body = null;
		if (contentType.includes("application/json")) {
			try {
				body = await response.json();
			} catch {
				throw new ApiError("unexpected", "The service returned an unreadable response.");
			}
		} else if (response.status !== 204) {
			try {
				body = await response.text();
			} catch {
				body = null;
			}
		}

		if (response.status === 404) throw new ApiError("not-found", "No matching record was found.");
		if (response.status === 401 || response.status === 403)
			throw new ApiError("unauthorized", "Authentication is required.");
		if (response.status === 422 || response.status === 400)
			throw new ApiError("validation", "Some submitted information needs to be checked.");
		if (!response.ok) throw new ApiError("server", "The service is temporarily unavailable.");
		if (
			body &&
			typeof body === "object" &&
			body.detail &&
			!Array.isArray(body.detail) &&
			typeof body.detail === "string"
		) {
			throw new ApiError("request", "The request could not be completed.");
		}
		return body;
	}

	function unwrap(payload) {
		if (!payload || typeof payload !== "object") return payload;
		return payload.data && typeof payload.data === "object" ? payload.data : payload;
	}

	function normalizeShipment(payload) {
		const data = unwrap(payload);
		const shipment = data && (data.shipment || data);
		if (!shipment || typeof shipment !== "object" || Array.isArray(shipment)) {
			throw new ApiError("unexpected", "The service returned an unexpected response.");
		}
		if (data.found === false || data.shipment === null)
			throw new ApiError("not-found", "No matching record was found.");

		const history =
			shipment.history ?? shipment.events ?? shipment.tracking_history ?? shipment.trackingHistory;
		return {
			trackingId: shipment.tracking_id ?? shipment.trackingId ?? shipment.id ?? "",
			status: shipment.current_status ?? shipment.currentStatus ?? shipment.status ?? "",
			description:
				shipment.status_description ?? shipment.statusDescription ?? shipment.description ?? "",
			lastUpdated:
				shipment.last_updated ??
				shipment.lastUpdated ??
				shipment.updated_at ??
				shipment.updatedAt ??
				"",
			history: Array.isArray(history)
				? history
						.map((event) => ({
							status: event.status ?? event.title ?? event.event ?? "",
							description: event.description ?? event.location ?? "",
							timestamp: event.timestamp ?? event.created_at ?? event.createdAt ?? event.date ?? "",
						}))
						.filter((event) => event.status || event.description || event.timestamp)
				: [],
		};
	}

	async function trackShipment(trackingId) {
		const id = String(trackingId || "").trim();
		if (!id) throw new ApiError("validation", "Enter a tracking ID to continue.");
		const path = settings.paths.tracking.replace("{trackingId}", encodeURIComponent(id));
		return normalizeShipment(await request(path));
	}

	async function warmBackend() {
		const healthUrl = endpoint(`/health?warmup=${Date.now()}`);
		const isCrossOrigin = new URL(healthUrl, window.location.href).origin !== window.location.origin;
		if (isCrossOrigin) {
			void fetch(healthUrl, {
				method: "GET",
				cache: "no-store",
				mode: "no-cors",
				keepalive: true,
			}).catch(() => {});
			return "contacted";
		}

		const controller = new AbortController();
		const timeout = window.setTimeout(() => controller.abort(), 15_000);
		try {
			const response = await fetch(healthUrl, {
				method: "GET",
				cache: "no-store",
				mode: "same-origin",
				signal: controller.signal,
				headers: { Accept: "application/json" },
			});
			if (!response.ok && response.type !== "opaque")
				throw new ApiError("server", "The service is not ready yet.");
			return "ready";
		} catch (error) {
			if (error instanceof ApiError) throw error;
			throw new ApiError("network", "The service is waking up.");
		} finally {
			window.clearTimeout(timeout);
		}
	}

	async function login(credentials) {
		return request(settings.paths.login, {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify(credentials),
		});
	}

	async function logout() {
		return request(settings.paths.logout, { method: "POST" });
	}

	async function listShipments() {
		const payload = unwrap(await request(settings.paths.shipments));
		const records = Array.isArray(payload)
			? payload
			: payload && (payload.shipments || payload.items);
		if (!Array.isArray(records))
			throw new ApiError("unexpected", "The service returned an unexpected response.");
		return records;
	}

	async function saveShipment(record, id = "") {
		const path = id
			? settings.paths.shipment.replace("{id}", encodeURIComponent(String(id)))
			: settings.paths.shipments;
		return request(path, {
			method: id ? "PUT" : "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify(record),
		});
	}

	async function deleteShipment(id) {
		const path = settings.paths.shipment.replace("{id}", encodeURIComponent(String(id)));
		return request(path, { method: "DELETE" });
	}

	window.CourierApi = Object.freeze({
		ApiError,
		warmBackend,
		trackShipment,
		login,
		logout,
		listShipments,
		saveShipment,
		deleteShipment,
	});
})();
