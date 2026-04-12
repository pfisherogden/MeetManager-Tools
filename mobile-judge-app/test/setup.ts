import { NativeModules } from "react-native";

// Mock window.dispatchEvent if it's missing (common in some Jest environments)
if (typeof window !== "undefined" && !window.dispatchEvent) {
	(window as any).dispatchEvent = jest.fn();
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
