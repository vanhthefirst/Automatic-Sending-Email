'use client'

import CSVUploadPortal from './components/csv_upload_portal'

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-between p-24">
      <CSVUploadPortal />
    </main>
  );
}