export default {
	addEventListener: jest.fn(() => jest.fn()),
	fetch: jest.fn(() =>
		Promise.resolve({
			type: "wifi",
			isConnected: true,
			isInternetReachable: true,
			details: {
				ssid: "test-ssid",
				bssid: "test-bssid",
				ipAddress: "192.168.1.1",
				subnet: "255.255.255.0",
				strength: 1,
				frequency: 1,
				linkSpeed: 1,
				rxLinkSpeed: 1,
				txLinkSpeed: 1,
			},
		}),
	),
	useNetInfo: jest.fn(() => ({
		type: "wifi",
		isConnected: true,
		isInternetReachable: true,
	})),
};
