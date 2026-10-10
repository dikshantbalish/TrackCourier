const API_ORIGIN = "https://trackcourier-6hcj.onrender.com";

export async function onRequest(context) {
	const requestUrl = new URL(context.request.url);
	const targetUrl = new URL(requestUrl.pathname + requestUrl.search, API_ORIGIN);
	const request = new Request(targetUrl, context.request);
	return fetch(request);
}
