import React, { useState, useCallback, useEffect } from 'react';
import { Upload, FileSpreadsheet, CheckCircle2, AlertCircle, Loader2, X } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';

interface FileState {
  file: File | null;
  uploading: boolean;
  error: string | null;
  success: boolean;
  isDragging: boolean;
  progress: number;
}

interface UploadedFile {
  name: string;
  size: string;
  status: 'Complete' | 'Processing' | 'Failed';
  date: string;
}

const CSVUploadPortal = () => {
  const [state, setState] = useState<FileState>({
    file: null,
    uploading: false,
    error: null,
    success: false,
    isDragging: false,
    progress: 0
  });

  const [recentFiles, setRecentFiles] = useState<UploadedFile[]>([
    { name: 'employees.csv', size: '245 KB', status: 'Complete', date: '2024-03-15' },
    { name: 'customers.csv', size: '182 KB', status: 'Processing', date: '2024-03-14' }
  ]);

  // Reset success/error messages after 5 seconds
  useEffect(() => {
    let timeout: NodeJS.Timeout;
    if (state.success || state.error) {
      timeout = setTimeout(() => {
        setState(prev => ({ ...prev, success: false, error: null }));
      }, 5000);
    }
    return () => clearTimeout(timeout);
  }, [state.success, state.error]);

  const validateFile = (file: File): string | null => {
    if (!file.name.toLowerCase().endsWith('.csv')) {
      return 'Please upload a CSV file';
    }
    if (file.size > 10 * 1024 * 1024) { // 10MB limit
      return 'File size must be less than 10MB';
    }
    return null;
  };

  const handleFileChange = useCallback((file: File) => {
    const error = validateFile(file);
    if (error) {
      setState(prev => ({ ...prev, error, file: null }));
      return;
    }

    setState(prev => ({ ...prev, file, uploading: true, error: null, progress: 0 }));
    
    // Simulate upload progress
    const interval = setInterval(() => {
      setState(prev => {
        if (prev.progress >= 100) {
          clearInterval(interval);
          // Add the file to recent uploads
          setRecentFiles(prevFiles => [{
            name: file.name,
            size: `${(file.size / 1024).toFixed(0)} KB`,
            status: 'Complete',
            date: new Date().toISOString().split('T')[0]
          }, ...prevFiles]);
          return { ...prev, uploading: false, success: true, file: null };
        }
        return { ...prev, progress: prev.progress + 5 };
      });
    }, 200);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setState(prev => ({ ...prev, isDragging: false }));
    const file = e.dataTransfer.files[0];
    if (file) handleFileChange(file);
  }, [handleFileChange]);

  const removeFile = useCallback((fileName: string) => {
    setRecentFiles(prev => prev.filter(file => file.name !== fileName));
  }, []);

  return (
    <Card className="w-full max-w-3xl mx-auto">
      <CardContent className="p-6 space-y-8">
        {/* Header */}
        <div className="space-y-3">
          <h1 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-primary to-primary/70 bg-clip-text text-transparent">
            CSV Upload Portal
          </h1>
          <p className="text-muted-foreground text-lg">
            Upload your CSV files for email automation
          </p>
        </div>

        {/* Status Messages */}
        {(state.error || state.success) && (
          <div className="relative">
            {state.error && (
              <Alert variant="destructive" className="animate-in slide-in-from-top-2">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{state.error}</AlertDescription>
              </Alert>
            )}
            
            {state.success && (
              <Alert className="bg-green-50 text-green-800 border-green-200 animate-in slide-in-from-top-2">
                <CheckCircle2 className="h-4 w-4 text-green-600" />
                <AlertDescription>File uploaded successfully!</AlertDescription>
              </Alert>
            )}
          </div>
        )}

        {/* Upload Area */}
        <div 
          onDrop={handleDrop}
          onDragOver={(e) => {
            e.preventDefault();
            setState(prev => ({ ...prev, isDragging: true }));
          }}
          onDragLeave={(e) => {
            e.preventDefault();
            setState(prev => ({ ...prev, isDragging: false }));
          }}
          className={`
            relative border-2 border-dashed rounded-xl p-10 transition-all duration-300
            ${state.isDragging 
              ? "border-primary bg-primary/5 scale-[1.02] shadow-lg" 
              : "border-muted hover:border-primary hover:bg-primary/5"
            }
            ${state.uploading ? "pointer-events-none opacity-75" : ""}
          `}
        >
          <div className="flex flex-col items-center justify-center gap-6">
            <div className={`
              h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center
              transition-transform duration-300
              ${state.isDragging ? "scale-110" : ""}
            `}>
              {state.uploading ? (
                <Loader2 className="h-8 w-8 text-primary animate-spin" />
              ) : (
                <Upload className="h-8 w-8 text-primary" />
              )}
            </div>
            
            <div className="text-center space-y-2">
              <h3 className="text-xl font-medium">
                {state.uploading ? "Uploading..." : "Drop your CSV file here"}
              </h3>
              <p className="text-sm text-muted-foreground">
                {state.uploading 
                  ? `${state.progress}% complete` 
                  : "or click to browse (max 10MB)"
                }
              </p>
            </div>

            {state.uploading && (
              <Progress 
                value={state.progress} 
                className="w-2/3 h-2"
              />
            )}
          </div>

          <input 
            type="file" 
            accept=".csv"
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleFileChange(file);
            }}
          />
        </div>

        {/* Recent Uploads */}
        {recentFiles.length > 0 && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-xl font-medium flex items-center gap-2">
                Recent Uploads
                <span className="text-sm text-muted-foreground font-normal">
                  ({recentFiles.length} files)
                </span>
              </h3>
              <Button 
                variant="ghost" 
                size="sm"
                onClick={() => setRecentFiles([])}
              >
                Clear All
              </Button>
            </div>
            
            <div className="space-y-3">
              {recentFiles.map((file, index) => (
                <div 
                  key={index} 
                  className="flex items-center justify-between p-4 bg-background rounded-lg border hover:shadow-md transition-shadow duration-200"
                >
                  <div className="flex items-center gap-4">
                    <div className="p-2 rounded-lg bg-primary/10">
                      <FileSpreadsheet className="h-6 w-6 text-primary" />
                    </div>
                    <div>
                      <p className="font-medium">{file.name}</p>
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <span>{file.size}</span>
                        <span>•</span>
                        <span>{file.date}</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="flex items-center gap-2">
                      {file.status === 'Processing' && (
                        <Loader2 className="h-4 w-4 text-primary animate-spin" />
                      )}
                      <span 
                        className={`
                          text-sm font-medium px-3 py-1 rounded-full
                          ${file.status === 'Complete' 
                            ? "bg-green-50 text-green-700" 
                            : file.status === 'Failed'
                            ? "bg-red-50 text-red-700"
                            : "bg-primary/10 text-primary"}
                        `}
                      >
                        {file.status}
                      </span>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 w-8 text-muted-foreground hover:text-destructive"
                      onClick={() => removeFile(file.name)}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default CSVUploadPortal;