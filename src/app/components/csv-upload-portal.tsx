import React, { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Upload, FileText, Loader2 } from 'lucide-react';
import { toast } from '@/hooks/use-toast';

interface UploadResponse {
  success: boolean;
  message: string;
  filename: string;
  timestamp: string;
  processed_rows: number;
  email_success?: number;
  email_failure?: number;
}

interface ErrorResponse {
  detail: string;
}

interface FileItem {
  name: string;
  size: number;
  status: 'complete' | 'processing' | 'error';
  message?: string;
}

const CSVUpload = () => {
  const [isMounted, setIsMounted] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<UploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [recentFiles, setRecentFiles] = useState<FileItem[]>([]);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  if (!isMounted) {
    return null;
  }

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0];
    if (selectedFile) {
      if (selectedFile.type === 'text/csv' || selectedFile.name.endsWith('.csv')) {
        setFile(selectedFile);
        setError(null);
        toast({
          title: "File selected",
          description: `${selectedFile.name} ready for upload`,
        });
      } else {
        setError('Please select a valid CSV file');
        setFile(null);
        toast({
          variant: "destructive",
          title: "Invalid file type",
          description: "Please select a CSV file",
        });
      }
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file first');
      toast({
        variant: "destructive",
        title: "No file selected",
        description: "Please select a file first",
      });
      return;
    }

    setLoading(true);
    setError(null);

    // Add file to recent uploads with 'processing' status
    const newFileItem: FileItem = {
      name: file.name,
      size: file.size,
      status: 'processing'
    };
    
    setRecentFiles(prev => [newFileItem, ...prev]);

    const formData = new FormData();
    formData.append('file', file);

    try {
      console.log('Sending request to backend...');
      const response = await fetch('http://localhost:8000/api/upload-csv', {
        method: 'POST',
        body: formData,
        headers: {
          'Accept': 'application/json',
        },
      });

      console.log('Response received:', response);
      const data = await response.json();

      if (!response.ok) {
        const errorData = data as ErrorResponse;
        throw new Error(errorData.detail || 'Upload failed');
      }

      setResult(data as UploadResponse);
      
      // Update the file status to 'complete'
      setRecentFiles(prev => 
        prev.map(f => 
          f.name === file.name 
            ? { ...f,
                status: 'complete',
                message: `Processed ${data.processed_rows + 1} rows. ${data.email_success || 0} emails sent.`
              } 
            : f
        )
      );
      
      toast({
        title: "Upload Successful",
        description: data.message,
      });

      // Clear the file input
      setFile(null);
      if (document.querySelector<HTMLInputElement>('input[type="file"]')) {
        (document.querySelector<HTMLInputElement>('input[type="file"]')!).value = '';
      }
      
    } catch (err) {
      console.error('Upload error:', err);
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      
      // Update file status to error
      setRecentFiles(prev => 
        prev.map(f => 
          f.name === file.name 
            ? { ...f, status: 'error', message: errorMessage } 
            : f
        )
      );

      setError(errorMessage);
      toast({
        variant: "destructive",
        title: "Upload Failed",
        description: errorMessage,
      });
    } finally {
      setLoading(false);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
  };

  return (
    <div className="min-h-screen w-full flex flex-col items-center px-4 sm:px-6 lg:px-8 bg-gray-50">
      <div className="w-full max-w-4xl mx-auto py-8">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold mb-2">CSV Upload Portal</h1>
          <p className="text-gray-600">Upload your CSV files for email automation</p>
        </div>

        <Card className="w-full bg-white shadow-lg p-6">
          <div 
            className="w-full border-2 border-dashed border-gray-200 rounded-lg p-8 text-center cursor-pointer hover:border-blue-400 transition-colors"
            onDragOver={(e) => {
              e.preventDefault();
              e.stopPropagation();
              e.currentTarget.classList.add('border-blue-400');
            }}
            onDragLeave={(e) => {
              e.preventDefault();
              e.stopPropagation();
              e.currentTarget.classList.remove('border-blue-400');
            }}
            onDrop={(e) => {
              e.preventDefault();
              e.stopPropagation();
              e.currentTarget.classList.remove('border-blue-400');
              const droppedFile = e.dataTransfer.files[0];
              if (droppedFile && (droppedFile.type === 'text/csv' || droppedFile.name.endsWith('.csv'))) {
                setFile(droppedFile);
                setError(null);
                toast({
                  title: "File dropped",
                  description: `${droppedFile.name} ready for upload`,
                });
              } else {
                setError('Please drop a valid CSV file');
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
              onClick={handleUpload} 
              disabled={loading || !file}
              className="w-full sm:w-64"
              variant={loading ? "outline" : "default"}
              size="lg"
            >
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Processing...
                </>
              ) : (
                'Upload and Process'
              )}
            </Button>
          </div>

          {error && (
            <Alert variant="destructive" className="mt-4">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
        </Card>

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
                      <p className="text-sm text-gray-500">{formatFileSize(file.size)}</p>
                      {file.message && (
                        <p className="text-sm text-gray-600 mt-1">{file.message}</p>
                      )}
                    </div>
                  </div>
                  <span className={`px-3 py-1 rounded-full text-sm ${
                    file.status === 'complete' 
                      ? 'bg-green-100 text-green-800'
                      : file.status === 'error'
                      ? 'bg-red-100 text-red-800'
                      : 'bg-blue-100 text-blue-800'
                  }`}>
                    {file.status === 'complete' ? 'Complete' : 
                     file.status === 'error' ? 'Error' : 'Processing'}
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