import React, { useState, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Upload, FileText, Loader2, Eye, Send } from "lucide-react";
import { toast } from "@/hooks/use-toast";
import EmailPreviewEditor from "./email_preview";

interface UploadResponse {
  success: boolean;
  message: string;
  filename: string;
  timestamp: string;
  processed_rows: number;
  email_success?: number;
  email_failure?: number;
}

interface PreviewResponse {
  success: boolean;
  chart: string;
  content: string;
  metrics: {
    total: number;
    completed: number;
    pending: number;
    past_due: number;
    completion_rate: number;
  };
}

interface ErrorResponse {
  detail: string;
}

interface FileItem {
  name: string;
  size: number;
  status: "complete" | "processing" | "error";
  message?: string;
}

interface EmailTemplate {
  subject: string;
  greeting: string;
  intro: string;
  action: string;
  closing: string;
}

// API endpoints configuration
const API_CONFIG = {
  BASE_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  API_KEY: process.env.NEXT_PUBLIC_API_KEY || "123",
  ENDPOINTS: {
    PREVIEW: "/api/preview-email",
    PROCESS: "/api/process-emails",
  },
};

const CSVUpload = () => {
  const [isMounted, setIsMounted] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<UploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [recentFiles, setRecentFiles] = useState<FileItem[]>([]);
  const [currentStep, setCurrentStep] = useState<
    "upload" | "preview" | "complete"
  >("upload");
  const [previewData, setPreviewData] = useState<PreviewResponse | null>(null);
  const [template, setTemplate] = useState<EmailTemplate>({
    subject: "Training Tasks Update",
    greeting: "Dear Team Leader,",
    intro: "This is a reminder about pending training tasks in your team:",
    action:
      "Please ensure your team completes any pending or past due tasks by this Friday.",
    closing: "Best regards,\nHR Team",
  });

  useEffect(() => {
    setIsMounted(true);
  }, []);

  if (!isMounted) {
    return null;
  }

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0];
    if (selectedFile) {
      if (
        selectedFile.type === "text/csv" ||
        selectedFile.name.endsWith(".csv")
      ) {
        setFile(selectedFile);
        setError(null);
        setCurrentStep("upload");
        toast({
          title: "File selected",
          description: `${selectedFile.name} ready for upload`,
        });
      } else {
        setError("Please select a valid CSV file");
        setFile(null);
        toast({
          variant: "destructive",
          title: "Invalid file type",
          description: "Please select a CSV file",
        });
      }
    }
  };

  const makeAPIRequest = async (endpoint: string, formData: FormData) => {
    try {
      const response = await fetch(`${API_CONFIG.BASE_URL}${endpoint}`, {
        method: "POST",
        headers: {
          "X-API-Key": API_CONFIG.API_KEY,
        },
        body: formData,
      });

      console.log("Response status:", response.status);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Request failed");
      }

      return await response.json();
    } catch (error) {
      console.error("API Request failed:", error);
      throw error;
    }
  };

  const handlePreview = async () => {
    if (!file) {
      setError("Please select a file first");
      return;
    }

    setLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append("file", file);
    // formData.append("template", JSON.stringify(template));

    try {
      const data = await makeAPIRequest(API_CONFIG.ENDPOINTS.PREVIEW, formData);
      setPreviewData(data);
      setCurrentStep("preview");
      toast({
        title: "Preview Generated",
        description: "You can now review and edit the email content",
      });
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to generate preview";
      setError(errorMessage);
      toast({
        variant: "destructive",
        title: "Preview Failed",
        description: errorMessage,
      });
    } finally {
      setLoading(false);
    }
  };

  const handleProcess = async () => {
    if (!file) return;

    setLoading(true);
    const formData = new FormData();
    formData.append("file", file);
    formData.append("template", JSON.stringify(template));

    // Add file to recent uploads
    const newFileItem: FileItem = {
      name: file.name,
      size: file.size,
      status: "processing",
    };

    setRecentFiles((prev) => [newFileItem, ...prev]);

    try {
      console.log("Making request to process emails");
      const data = await makeAPIRequest(API_CONFIG.ENDPOINTS.PROCESS, formData);
      setResult(data);
      setCurrentStep("complete");

      // Update file status
      setRecentFiles((prev) =>
        prev.map((f) =>
          f.name === file.name
            ? {
                ...f,
                status: "complete",
                message: `Processed ${data.processed_rows} rows. ${data.email_success} emails sent successfully, ${data.email_failure} failed.`,
              }
            : f
        )
      );

      toast({
        title: "Processing Complete",
        description: `Successfully sent ${data.email_success} emails`,
      });

      // Clear file input
      setFile(null);
      if (document.querySelector<HTMLInputElement>('input[type="file"]')) {
        document.querySelector<HTMLInputElement>('input[type="file"]')!.value =
          "";
      }
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Unknown error occurred";

      // Update file status to error
      setRecentFiles((prev) =>
        prev.map((f) =>
          f.name === file.name
            ? { ...f, status: "error", message: errorMessage }
            : f
        )
      );

      setError(errorMessage);
      toast({
        variant: "destructive",
        title: "Processing Failed",
        description: errorMessage,
      });
    } finally {
      setLoading(false);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
  };

  const handleBackToUpload = () => {
    setCurrentStep("upload");
    setPreviewData(null);
    setError(null);
  };

  return (
    <div className="min-h-screen w-full flex flex-col items-center px-4 sm:px-6 lg:px-8 bg-gray-50">
      <div className="w-full max-w-4xl mx-auto py-8">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold mb-2">CSV Upload Portal</h1>
          <p className="text-gray-600">
            Upload your CSV files for email automation
          </p>
        </div>

        {currentStep === "upload" && (
          <Card className="w-full bg-white shadow-lg p-6">
            <div
              className="w-full border-2 border-dashed border-gray-200 rounded-lg p-8 text-center cursor-pointer hover:border-blue-400 transition-colors"
              onDragOver={(e) => {
                e.preventDefault();
                e.stopPropagation();
                e.currentTarget.classList.add("border-blue-400");
              }}
              onDragLeave={(e) => {
                e.preventDefault();
                e.stopPropagation();
                e.currentTarget.classList.remove("border-blue-400");
              }}
              onDrop={(e) => {
                e.preventDefault();
                e.stopPropagation();
                e.currentTarget.classList.remove("border-blue-400");
                const droppedFile = e.dataTransfer.files[0];
                if (
                  droppedFile &&
                  (droppedFile.type === "text/csv" ||
                    droppedFile.name.endsWith(".csv"))
                ) {
                  setFile(droppedFile);
                  setError(null);
                  toast({
                    title: "File dropped",
                    description: `${droppedFile.name} ready for upload`,
                  });
                } else {
                  setError("Please drop a valid CSV file");
                  toast({
                    variant: "destructive",
                    title: "Invalid file type",
                    description: "Please drop a CSV file",
                  });
                }
              }}
            >
              <div className="flex flex-col items-center justify-center min-h-[200px] space-y-4">
                <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mb-4">
                  <Upload className="w-8 h-8 text-blue-500" />
                </div>
                <h3 className="text-lg font-medium">Drop your CSV file here</h3>
                <p className="text-gray-500">or</p>
                <label className="cursor-pointer">
                  <span className="text-blue-500 hover:text-blue-600 font-medium">
                    click to browse
                  </span>
                  <input
                    type="file"
                    className="hidden"
                    accept=".csv"
                    onChange={handleFileChange}
                  />
                </label>
                {file && (
                  <div className="text-sm text-gray-600 mt-2">
                    Selected: {file.name} ({formatFileSize(file.size)})
                  </div>
                )}
              </div>
            </div>

            <div className="flex justify-center mt-6">
              <Button
                onClick={handlePreview}
                disabled={loading || !file}
                className="w-full sm:w-64"
                variant={loading ? "outline" : "default"}
                size="lg"
              >
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Generating Preview...
                  </>
                ) : (
                  <>
                    <Eye className="mr-2 h-4 w-4" />
                    Preview Emails
                  </>
                )}
              </Button>
            </div>
          </Card>
        )}

        {currentStep === "preview" && previewData && (
          <div className="space-y-6">
            <Card className="w-full bg-white shadow-lg p-6">
              <div className="flex justify-between items-center mb-4">
                <Button
                  variant="outline"
                  onClick={handleBackToUpload}
                  size="sm"
                >
                  Back to Upload
                </Button>
              </div>
              <EmailPreviewEditor
                emailContent={template.intro}
                onContentChange={(content: string) =>
                  setTemplate((prev) => ({ ...prev, intro: content }))
                }
                onProcess={handleProcess}
                previewChart={previewData.chart}
                metrics={previewData.metrics}
              />
            </Card>
          </div>
        )}

        {error && (
          <Alert variant="destructive" className="mt-4">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Recent Uploads section */}
        {recentFiles.length > 0 && (
          <div className="mt-8">
            <h2 className="text-xl font-semibold mb-4">Recent Uploads</h2>
            <div className="space-y-3">
              {recentFiles.map((file, index) => (
                <div
                  key={`${file.name}-${index}`}
                  className="flex items-center justify-between p-4 bg-white rounded-lg shadow-sm"
                >
                  <div className="flex items-center space-x-3">
                    <FileText className="w-5 h-5 text-blue-500" />
                    <div>
                      <p className="font-medium">{file.name}</p>
                      <p className="text-sm text-gray-500">
                        {formatFileSize(file.size)}
                      </p>
                      {file.message && (
                        <p className="text-sm text-gray-600 mt-1">
                          {file.message}
                        </p>
                      )}
                    </div>
                  </div>
                  <span
                    className={`px-3 py-1 rounded-full text-sm ${
                      file.status === "complete"
                        ? "bg-green-100 text-green-800"
                        : file.status === "error"
                        ? "bg-red-100 text-red-800"
                        : "bg-blue-100 text-blue-800"
                    }`}
                  >
                    {file.status === "complete"
                      ? "Complete"
                      : file.status === "error"
                      ? "Error"
                      : "Processing"}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default CSVUpload;
