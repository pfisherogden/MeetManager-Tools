// Client-side stub of actions for static export mode (Tauri compilation)
// This prevents Server Actions compilation errors and server-only dependencies on the client bundle.

export async function generateReport(_config: any) {
	return null;
}

export async function getTeams() {
	return { teams: [] };
}

export async function getTeam(_id: number) {
	return null;
}

export async function getMeets() {
	return { meets: [] };
}

export async function getAthletes() {
	return { athletes: [] };
}

export async function getEvents() {
	return { events: [] };
}

export async function getSessions() {
	return { sessions: [] };
}

export async function getRelays(_eventId?: string) {
	return { relays: [] };
}

export async function getScores() {
	return { scores: [] };
}

export async function getEventScores() {
	return { scores: [] };
}

export async function uploadDataset(_formData: FormData) {
	return null;
}

export async function uploadDatasetFromDrive(
	_fileId: string,
	_filename: string,
) {
	return null;
}

export async function listDatasets() {
	return { datasets: [] };
}

export async function setActiveDataset(_filename: string) {
	return null;
}

export async function deleteDataset(_filename: string) {
	return null;
}

export async function generateReportBundle(_config: any) {
	return null;
}

export async function getJobStatus(_jobId: string) {
	return null;
}

export async function getDashboardStats() {
	return {
		meetCount: 0,
		teamCount: 0,
		athleteCount: 0,
		eventCount: 0,
		totalAthletes: 0,
		totalTeams: 0,
		totalEvents: 0,
		totalResults: 0,
	};
}

export async function publishMeetData(_filename: string, _baseUrl: string) {
	return null;
}

export async function getAdminConfig() {
	return null;
}

export async function getAthlete(_id: number) {
	return null;
}

export async function getEntries(_eventId?: string, _athleteId?: string) {
	return { entries: [] };
}

export async function updateAdminConfig(_name: string, _desc?: string) {
	return null;
}

export async function getDisqualifications() {
	return [];
}

export async function deleteDq(_dqId: string) {
	return null;
}

export async function clearAllDqs() {
	return null;
}

export async function validateActiveMeet() {
	return { errors: [] };
}
