import React, { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';  
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Eye, Send } from 'lucide-react';


interface EmailPreviewEditorProps {
    emailContent: string;
    onContentChange: (content: string) => void;
    onProcess: (sendTest?: boolean) => Promise<void>;
    previewChart: string;
    metrics: {
      total: number;
      completed: number;
      pending: number;
      past_due: number;
      completion_rate: number;
    };
  }

  interface EmailTemplate {
    subject: string;
    greeting: string;
    intro: string;
    action: string;
    closing: string;
}

const EmailPreviewEditor: React.FC<EmailPreviewEditorProps> = ({ 
  emailContent, 
  onContentChange, 
  onProcess,
  previewChart,
  metrics 
}) => {
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [sendTestEmail, setSendTestEmail] = useState(false);
  
  const defaultEmailTemplate = {
    subject: "Training Tasks Update",
    greeting: "Dear Team Leader,",
    intro: "This is a reminder about pending training tasks in your team:",
    action: "Please ensure your team completes any pending or past due tasks by this Friday.\nBelow is the chart to show the current status of your team and others:",
    closing: "Best regards,\nHR Team"
  };

  const [template, setTemplate] = useState<EmailTemplate>(defaultEmailTemplate);

  const MetricsDisplay = () => (
    <div className="bg-gray-50 p-5 rounded-lg my-5">
      <p><strong>Total Tasks:</strong> {metrics.total}</p>
      <p><strong>Completed:</strong> {metrics.completed} ({metrics.completion_rate.toFixed(2)}%)</p>
      <p><strong>Pending:</strong> {metrics.pending}</p>
      <p><strong>Past Due:</strong> {metrics.past_due}</p>
    </div>
  );

  const handleTemplateChange = (field: keyof EmailTemplate, value: string) => {
    const newTemplate = { ...template, [field]: value };
    setTemplate(newTemplate);

    const metricsHtml = `
      <p><strong>Total Tasks:</strong> ${metrics.total}</p>
      <p><strong>Completed:</strong> ${metrics.completed} (${metrics.completion_rate.toFixed(2)}%)</p>
      <p><strong>Pending:</strong> ${metrics.pending}</p>
      <p><strong>Past Due:</strong> ${metrics.past_due}</p>
    `;
    
    // Generate new HTML content
    const newContent = `
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto;">
                <h2 style="color: #2c3e50;">${newTemplate.subject}</h2>
                <p>${newTemplate.greeting}</p>
                <p>${newTemplate.intro}</p>
                
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0;">
                        ${metricsHtml}
                </div>
                
                <p>${newTemplate.action}</p>
                <img src="cid:task_chart" style="max-width: 100%; height: auto;">
                
                <p style="margin-top: 20px;">${newTemplate.closing}</p>
        </body>
        </html>
    `;
    
    onContentChange(newContent);
  };

  const handleSendEmail = async () => {
    try {
      // If sendTestEmail is true, send with template data of all zeros
      const emailData = sendTestEmail ? {
        ...template,
        metrics: {
          total: 0,
          completed: 0,
          pending: 0,
          past_due: 0,
          completion_rate: 0
        },
        sendTestCopy: true
      } : {
        ...template,
        metrics,
        sendTestCopy: false
      };

      await onProcess(sendTestEmail);
      
      // Additional API call for test email if checkbox is checked
      if (sendTestEmail) {
        await fetch('/api/send-test-email', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(emailData),
        });
      }
    } catch (error) {
      console.error('Error sending email:', error);
    }
  };

  return (
    <div className="space-y-6">
      <Tabs defaultValue="edit" className="w-full">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="edit">Edit Template</TabsTrigger>
          <TabsTrigger value="preview">Preview</TabsTrigger>
        </TabsList>
        
        <TabsContent value="edit" className="space-y-4">
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium">Subject</label>
              <Textarea
                value={template.subject}
                onChange={(e) => handleTemplateChange('subject', e.target.value)}
                className="h-10"
              />
            </div>
            <div>
              <label className="text-sm font-medium">Greeting</label>
              <Textarea
                value={template.greeting}
                onChange={(e) => handleTemplateChange('greeting', e.target.value)}
                className="h-10"
              />
            </div>
            <div>
              <label className="text-sm font-medium">Introduction</label>
              <Textarea
                value={template.intro}
                onChange={(e) => handleTemplateChange('intro', e.target.value)}
                className="h-20"
              />
            </div>
            <div>
              <label className="text-sm font-medium">Call to Action</label>
              <Textarea
                value={template.action}
                onChange={(e) => handleTemplateChange('action', e.target.value)}
                className="h-20"
              />
            </div>
            <div>
              <label className="text-sm font-medium">Closing</label>
              <Textarea
                value={template.closing}
                onChange={(e) => handleTemplateChange('closing', e.target.value)}
                className="h-20"
              />
            </div>
          </div>
        </TabsContent>
        
        <TabsContent value="preview">
          <Card className="p-6">
            <h2 className="text-2xl font-semibold text-[#2c3e50] mb-4">{template.subject}</h2>
            <div className="space-y-4">
              <p>{template.greeting}</p>
              <p>{template.intro}</p>
              <MetricsDisplay />
              <p>{template.action}</p>
              {previewChart && (
                <div className="my-4">
                  <img 
                    src={`data:image/png;base64,${previewChart}`} 
                    alt="Task Status Chart"
                    className="max-w-full"
                  />
                </div>
              )}
              <p className="mt-5 whitespace-pre-line">{template.closing}</p>
            </div>
          </Card>
        </TabsContent>
      </Tabs>

      <div className="flex flex-col space-y-4">
        <div className="flex items-center space-x-2">
          <Checkbox
            id="send-test"
            checked={sendTestEmail}
            onCheckedChange={(checked) => setSendTestEmail(checked as boolean)}
          />
          <label
            htmlFor="send-test"
            className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
          >
            Send me a copy with template data
          </label>
        </div>

        <div className="flex justify-end space-x-4">
          <Button
            variant="outline"
            onClick={() => setIsPreviewOpen(true)}
            className="w-32"
          >
            <Eye className="w-4 h-4 mr-2" />
            Preview
          </Button>
          <Button
            onClick={handleSendEmail}
            className="w-32"
          >
            <Send className="w-4 h-4 mr-2" />
            Send
          </Button>
        </div>
      </div>

      <Dialog open={isPreviewOpen} onOpenChange={setIsPreviewOpen}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>Email Preview</DialogTitle>
          </DialogHeader>
          <div className="mt-4">
            <Card className="p-6">
              <h2 className="text-2xl font-semibold mb-4">{template.subject}</h2>
              <div className="space-y-4">
                <p>{template.greeting}</p>
                <p>{template.intro}</p>
                <MetricsDisplay />
                <p>{template.action}</p>
                {previewChart && (
                  <div className="my-4">
                    <img 
                      src={`data:image/png;base64,${previewChart}`} 
                      alt="Task Status Chart"
                      className="max-w-full"
                    />
                  </div>
                )}
                <p className="mt-5 whitespace-pre-line">{template.closing}</p>
              </div>
            </Card>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default EmailPreviewEditor;