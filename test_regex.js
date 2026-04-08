const ALLOWED_HOSTS = [
	"localhost",
	"127.0.0.1",
	"pfisherogden.github.io",
	"storage.googleapis.com",
	"example.com", // For testing
];

const validateUrl = (url) => {
	try {
		// Use regex to extract hostname safely
		const match = url.match(/^(?:https?:\/\/)?(?:[^@\n]+@)?(?:www\.)?([^:\/\n?]+)/im);
		const hostname = match ? match[1] : "";
        console.log(`URL: ${url}`);
        console.log(`Matched Hostname: ${hostname}`);
		return ALLOWED_HOSTS.includes(hostname.toLowerCase());
	} catch (e) {
		console.warn(`Invalid URL format: ${url}`);
		return false;
	}
};

const testUrl = "https://storage.googleapis.com/mmtools-data-mmtools-488404/users/EDsgBfNXwWOpiL9Q9NQjYURoavW2/published/program_after%20meet%20-%20TVSL%20Championship%20Meet%20July%2019%2C%202025.mdb.json?GoogleAccessId=...&Expires=...&Signature=...";
console.log(`Result: ${validateUrl(testUrl)}`);
