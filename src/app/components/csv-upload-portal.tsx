import React, { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Upload, FileText, Loader2 } from 'lucide-react';

interface UploadResponse {
  message: string;
  data?: {
    total_rows: number;
    total_columns: number;
    columns: string[];
    summary_statistics: Record<string, any>;
  };
}

interface ErrorResponse {
  detail: string;
}

interface FileItem {
  name: string;
  size: number;
  status: 'complete' | 'processing';
}

const CSVUpload = () => {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<UploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [recentFiles, setRecentFiles] = useState<FileItem[]>([]);


  interface FileChangeEvent extends React.ChangeEvent<HTMLInputElement> {
    target: HTMLInputElement & { files: FileList };
  }

  const handleFileChange = (event: FileChangeEvent) => {
    const selectedFile = event.target.files[0];
    if (selectedFile && selectedFile.type === 'text/csv') {
      setFile(selectedFile);
      setError(null);
    } else {
      setError('Please select a valid CSV file');
      setFile(null);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file first');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    // First add the file to recent uploads with 'processing' status
    const newFileItem: FileItem = {
      name: file.name,
      size: file.size,
      status: 'processing'
    };
    
    setRecentFiles(prev => [newFileItem, ...prev]);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('http://localhost:8000/api/upload-csv', {
        method: 'POST',
        body: formData,
        headers: {
          'Accept': 'application/json',
        },
      });

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
            ? { ...f, status: 'complete' } 
            : f
        )
      );

      // Clear the file input
      setFile(null);
      
    } catch (err) {
      console.error('Upload error:', err);
      setError(
        'Failed to upload and process file: ' + 
        (err instanceof Error ? err.message : 'Unknown error')
      );
    } finally {
      setLoading(false);
    }
  };

  const formatFileSize = (bytes: number) => {
    return `${Math.round(bytes / 1024)} KB`;
  };

  return (
    <div className="min-h-screen w-full flex flex-col items-center px-4 sm:px-6 lg:px-8">
      <div className="w-full max-w-4xl mx-auto py-8">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-semibold mb-2">CSV Upload Portal</h1>
          <p className="text-gray-500">Upload your CSV files for email automation</p>
        </div>

        <Card className="w-full bg-white shadow-lg">
          <div 
            className="w-full border-2 border-dashed border-gray-200 rounded-lg p-8 text-center"
            onDragOver={(e) => {
              e.preventDefault();
              e.stopPropagation();
            }}
            onDrop={(e) => {
              e.preventDefault();
              e.stopPropagation();
              const droppedFile = e.dataTransfer.files[0];
              if (droppedFile && droppedFile.type === 'text/csv') {
                setFile(droppedFile);
                setError(null);
              } else {
                setError('Please drop a valid CSV file');
              }
            }}
          >
            <div className="flex flex-col items-center justify-center min-h-[200px]">
              <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mb-4">
                <Upload className="w-8 h-8 text-blue-500" />
              </div>
              <h3 className="text-lg font-medium mb-1">Drop your CSV file here</h3>
              <p className="text-gray-500 mb-4">or</p>
              <label className="cursor-pointer text-blue-500 hover:text-blue-600">
                click to browse
                <input
                  type="file"
                  className="hidden"
                  accept=".csv"
                  onChange={handleFileChange}
                />
              </label>
            </div>
          </div>

          {file && (
            <div className="text-sm text-gray-500 mt-4 text-center">
              Selected file: {file.name}
            </div>
          )}

          <div className="flex justify-center my-6">
            <Button 
              onClick={handleUpload} 
              disabled={loading || !file}
              className="w-full mx-8 sm:w-48 h-10 bg-blue-500 hover:bg-blue-600"
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
            <Alert variant="destructive" className="mt-4 mx-8 mb-6">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
        </Card>

        {/* Recent Uploads section */}
        {recentFiles.length > 0 && (
          <div className="mt-8 w-full">
            <h2 className="text-lg font-semibold mb-4">Recent Uploads</h2>
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
                    </div>
                  </div>
                  <span className={`text-sm ${
                    file.status === 'complete' 
                      ? 'text-green-500' 
                      : 'text-blue-500'
                  }`}>
                    {file.status === 'complete' ? 'Complete' : 'Processing'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {loading && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
          <div className="bg-white p-4 rounded-lg flex items-center space-x-2">
            <Loader2 className="animate-spin h-5 w-5" />
            <span>Processing...</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default CSVUpload;