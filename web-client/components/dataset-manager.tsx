"use client"

import { useState, useEffect, useRef } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { toast } from "sonner"
import { listDatasets, setActiveDataset, uploadDataset } from "@/app/actions"
import { Loader2, Upload, Check, Database } from "lucide-react"
import { formatDistanceToNow } from "date-fns"

interface Dataset {
    filename: string;
    isActive: boolean;
    lastModified?: string;
}

export function DatasetManager() {
    const [datasets, setDatasets] = useState<Dataset[]>([])
    const [loading, setLoading] = useState(true)
    const [uploading, setUploading] = useState(false)
    const fileInputRef = useRef<HTMLInputElement>(null)

    const fetchDatasets = async () => {
        try {
            setLoading(true)
            const res: any = await listDatasets()
            if (res && res.datasets) {
                setDatasets(res.datasets)
            }
        } catch (error) {
            console.error(error)
            toast.error("Failed to load datasets")
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        fetchDatasets()
    }, [])

    const handleSetActive = async (filename: string) => {
        try {
            await setActiveDataset(filename)
            toast.success(`Active dataset changed to ${filename}`)
            fetchDatasets()
        } catch (error) {
            console.error(error)
            toast.error("Failed to set active dataset")
        }
    }

    const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0]
        if (!file) return

        if (!file.name.endsWith('.mdb')) {
            toast.error("Invalid file type. Please upload an .mdb file.")
            return
        }

        const formData = new FormData()
        formData.append('file', file)

        setUploading(true)
        try {
            await uploadDataset(formData)
            toast.success("Dataset uploaded successfully")
            if (fileInputRef.current) fileInputRef.current.value = ''
            fetchDatasets()
        } catch (error: any) {
            console.error(error)
            toast.error(`Upload failed: ${error.message}`)
        } finally {
            setUploading(false)
        }
    }

    return (
        <Card>
            <CardHeader className="flex flex-row items-center justify-between">
                <div>
                    <CardTitle>Dataset Management</CardTitle>
                    <CardDescription>Upload and manage MDB database files</CardDescription>
                </div>
                <div>
                    <Input
                        type="file"
                        accept=".mdb"
                        className="hidden"
                        ref={fileInputRef}
                        onChange={handleUpload}
                    />
                    <Button
                        disabled={uploading}
                        onClick={() => fileInputRef.current?.click()}
                    >
                        {uploading ? (
                            <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                Uploading...
                            </>
                        ) : (
                            <>
                                <Upload className="mr-2 h-4 w-4" />
                                Upload Dataset
                            </>
                        )}
                    </Button>
                </div>
            </CardHeader>
            <CardContent>
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead>Filename</TableHead>
                            <TableHead>Status</TableHead>
                            <TableHead>Last Modified</TableHead>
                            <TableHead className="text-right">Actions</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {loading ? (
                            <TableRow>
                                <TableCell colSpan={4} className="text-center py-8">
                                    <Loader2 className="h-6 w-6 animate-spin mx-auto text-muted-foreground" />
                                </TableCell>
                            </TableRow>
                        ) : datasets.length === 0 ? (
                            <TableRow>
                                <TableCell colSpan={4} className="text-center py-8 text-muted-foreground">
                                    No datasets found. Upload one to get started.
                                </TableCell>
                            </TableRow>
                        ) : (
                            datasets.map((dataset) => (
                                <TableRow key={dataset.filename}>
                                    <TableCell className="font-medium flex items-center gap-2">
                                        <Database className="h-4 w-4 text-muted-foreground" />
                                        {dataset.filename}
                                    </TableCell>
                                    <TableCell>
                                        {dataset.isActive && (
                                            <Badge variant="secondary" className="gap-1 bg-green-100 text-green-800 hover:bg-green-100 uppercase text-[10px]">
                                                <Check className="h-3 w-3" /> Active
                                            </Badge>
                                        )}
                                    </TableCell>
                                    <TableCell className="text-muted-foreground text-sm">
                                        {dataset.lastModified ? (
                                            (() => {
                                                const ts = parseFloat(dataset.lastModified);
                                                if (!isNaN(ts) && ts > 0) {
                                                    return formatDistanceToNow(new Date(ts * 1000), { addSuffix: true });
                                                }
                                                return '-';
                                            })()
                                        ) : '-'}
                                    </TableCell>
                                    <TableCell className="text-right">
                                        {!dataset.isActive && (
                                            <Button
                                                variant="outline"
                                                size="sm"
                                                onClick={() => handleSetActive(dataset.filename)}
                                            >
                                                Set Active
                                            </Button>
                                        )}
                                    </TableCell>
                                </TableRow>
                            ))
                        )}
                    </TableBody>
                </Table>
            </CardContent>
        </Card>
    )
}
