"use client"

import { useState, useEffect } from "react"
import { AppSidebar } from "@/components/app-sidebar"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { FileJson, RefreshCw, Upload, Check } from "lucide-react"
import { listDatasets, setActiveDataset, uploadDataset } from "../actions"

export default function AdminPage() {
    const [datasets, setDatasets] = useState<any[]>([])
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [uploadStatus, setUploadStatus] = useState<string | null>(null)

    const fetchDatasets = async () => {
        setLoading(true)
        setError(null)
        try {
            const response: any = await listDatasets();
            setDatasets(response.datasets || []);
        } catch (e: any) {
            console.error("Error fetching datasets:", e)
            setError(e.message || "Failed to fetch datasets")
        } finally {
            setLoading(false)
        }
    }

    const handleSetActive = async (filename: string) => {
        setLoading(true)
        try {
            await setActiveDataset(filename);
            await fetchDatasets()
        } catch (e: any) {
            setError(`Failed to set active dataset: ${e.message}`)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        fetchDatasets()
    }, [])

    return (
        <div className="flex min-h-screen bg-background">
            <AppSidebar />
            <main className="flex-1 flex flex-col p-6">
                <div className="mb-6 flex items-center justify-between">
                    <div>
                        <h1 className="text-2xl font-bold">Admin Controls</h1>
                        <p className="text-muted-foreground">Manage server data source</p>
                    </div>
                    <Button variant="outline" onClick={fetchDatasets} disabled={loading}>
                        <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                        Refresh
                    </Button>
                </div>

                {error && (
                    <div className="bg-destructive/10 text-destructive p-4 rounded-md mb-6">
                        {error}
                    </div>
                )}

                {/* Upload Section */}
                <div className="mb-8 p-6 bg-white rounded-lg shadow-sm border border-gray-100">
                    <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
                        <Upload className="h-5 w-5" />
                        Upload Dataset
                    </h2>
                    <p className="text-sm text-muted-foreground mb-4">
                        Upload an .mdb file (Microsoft Access) to import a new meet.
                    </p>
                    <form action={async (formData) => {
                        setUploadStatus('Uploading...');
                        try {
                            await uploadDataset(formData);
                            setUploadStatus('Upload complete!');
                            setTimeout(() => setUploadStatus(null), 3000);
                            fetchDatasets();
                        } catch (e: any) {
                            setUploadStatus('Upload failed: ' + e);
                        }
                    }} className="flex gap-4 items-center">
                        <input
                            type="file"
                            name="file"
                            accept=".mdb"
                            className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100"
                        />
                        <button type="submit" className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 transition-colors disabled:opacity-50">
                            Upload
                        </button>
                    </form>
                    {uploadStatus && (
                        <p className={`mt-2 text-sm ${uploadStatus.includes('failed') ? 'text-red-500' : 'text-green-600'}`}>
                            {uploadStatus}
                        </p>
                    )}

                </div>

                <div className="bg-card border rounded-lg overflow-hidden">
                    <div className="p-4 border-b bg-muted/20 font-medium">Available Datasets</div>
                    <ul>
                        {datasets.map((ds) => (
                            <li key={ds.filename} className="flex items-center justify-between p-4 border-b last:border-0 hover:bg-muted/10 transition-colors">
                                <div className="flex items-center gap-3">
                                    <FileJson className="h-5 w-5 text-blue-500" />
                                    <div className="flex flex-col">
                                        <span className={ds.isActive ? "font-bold" : ""}>{ds.filename}</span>
                                        <span className="text-xs text-muted-foreground">
                                            Modified: {new Date(Number(ds.lastModified) * 1000).toLocaleString()}
                                        </span>
                                    </div>
                                </div>

                                {ds.isActive ? (
                                    <span className="flex items-center text-green-600 bg-green-100 px-3 py-1 rounded-full text-xs font-medium">
                                        <Check className="h-3 w-3 mr-1" />
                                        Active
                                    </span>
                                ) : (
                                    <Button size="sm" variant="ghost" onClick={() => handleSetActive(ds.filename)}>
                                        Load
                                    </Button>
                                )}
                            </li>
                        ))}
                    </ul>
                    {datasets.length === 0 && !loading && (
                        <div className="p-8 text-center text-muted-foreground">No datasets found in backend/data</div>
                    )}
                </div>
            </main>
        </div>
    )
}
