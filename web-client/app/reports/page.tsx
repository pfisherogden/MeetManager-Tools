import { AppSidebar } from "@/components/app-sidebar"
import { ReportsManager } from "@/components/reports-manager"

export const dynamic = 'force-dynamic';

export default async function ReportsPage() {
    return (
        <div className="flex min-h-screen bg-background text-foreground">
            <AppSidebar />
            <main className="flex-1 flex flex-col overflow-hidden">
                <div className="p-6 pb-0">
                    <h1 className="text-2xl font-bold">Reports</h1>
                    <p className="text-muted-foreground">Generate and customize PDF reports from meet data</p>
                </div>
                <ReportsManager />
            </main>
        </div>
    )
}
