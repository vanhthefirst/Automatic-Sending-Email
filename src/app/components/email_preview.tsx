import React, { useState, useEffect } from 'react';
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
    onProcess: (emailData: any) => Promise<void>;
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
  const [previewContent, setPreviewContent] = useState(emailContent);

  const [template, setTemplate] = useState<EmailTemplate>({
    subject: "Training Tasks Update",
    greeting: "Dear Team Leader,",
    intro: "This is a reminder about pending training tasks in your team:",
    action: "Please ensure your team completes any pending or past due tasks by this Friday.\nBelow is the chart to show the current status of your team and others:",
    closing: "Best regards,\nHR Team"
  });

  useEffect(() => {
    const formatText = (text: string) => {
      return text.split('\n').map(line => `<p>${line}</p>`).join('');
    };

    const updatedContent = `
      <html>
      <body style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto;">
        <h1 style="color: #2c3e50; font-size: 28px; font-weight: bold; margin-bottom: 24px;">${template.subject}</h1>
        ${formatText(template.greeting)}
        ${formatText(template.intro)}
        
        <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0;">
          <p><strong>Total Tasks:</strong> ${metrics.total}</p>
          <p><strong>Completed:</strong> ${metrics.completed} (${metrics.completion_rate.toFixed(2)}%)</p>
          <p><strong>Pending:</strong> ${metrics.pending}</p>
          <p><strong>Past Due:</strong> ${metrics.past_due}</p>
        </div>
        
        ${formatText(template.action)}
        ${previewChart ? `<img src="data:image/png;base64,${previewChart}" style="max-width: 100%; height: auto;">` : ''}
        
        ${formatText(template.closing)}
      </body>
      </html>
    `;
    setPreviewContent(updatedContent);
    onContentChange(updatedContent);
  }, [template, metrics, previewChart]);

  const handleTemplateChange = (field: keyof EmailTemplate, value: string) => {
    setTemplate(prev => ({ ...prev, [field]: value }));
  };

  const handleSendEmail = async () => {
    try {
      const emailData = {
        ...template,
        sendTestCopy: sendTestEmail
      };

      console.log("Sending email with test flag:", sendTestEmail);
      await onProcess(emailData); // Pass the complete emailData instead of just the flag
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
            <div dangerouslySetInnerHTML={{ __html: emailContent }} />
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
            <div dangerouslySetInnerHTML={{ __html: emailContent }} />
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default EmailPreviewEditor;