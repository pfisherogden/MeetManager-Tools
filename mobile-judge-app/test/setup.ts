import { NativeModules } from "react-native";

// Mock window.dispatchEvent and other browser globals
if (typeof window !== "undefined") {
	if (!window.dispatchEvent) {
		(window as any).dispatchEvent = jest.fn();
	}
}

// Ensure localStorage is mocked properly for Node/Jest
const mockLocalStorage = {
	getItem: jest.fn(),
	setItem: jest.fn(),
	removeItem: jest.fn(),
	clear: jest.fn(),
};

Object.defineProperty(global, "localStorage", {
	value: mockLocalStorage,
	writable: true,
});

if (typeof window !== "undefined") {
	Object.defineProperty(window, "localStorage", {
		value: mockLocalStorage,
		writable: true,
	});
}

// Mock window.location
const mockLocation = {
	search: "",
	pathname: "/",
	reload: jest.fn(),
};

Object.defineProperty(global, "location", {
	value: mockLocation,
	writable: true,
});

if (typeof window !== "undefined") {
	Object.defineProperty(window, "location", {
		value: mockLocation,
		writable: true,
	});
}

// Mock NativeModules if they are missing
NativeModules.NativeUnimoduleProxy = NativeModules.NativeUnimoduleProxy || {};

jest.mock("@expo/vector-icons", () => ({
	Ionicons: "Ionicons",
	AntDesign: "AntDesign",
	MaterialIcons: "MaterialIcons",
}));

jest.mock("expo-font", () => ({
	loadAsync: jest.fn(),
	isLoaded: jest.fn(() => true),
}));

jest.mock("expo-modules-core", () => {
	const actual = jest.requireActual("expo-modules-core");
	return {
		...actual,
		NativeModulesProxy: {},
		EventEmitter: class {
			addListener = jest.fn();
			removeListeners = jest.fn();
			removeAllListeners = jest.fn();
			emit = jest.fn();
		},
	};
});
