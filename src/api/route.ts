import { exec } from 'child_process';
import { NextResponse } from 'next/server';
import { promisify } from 'util';

const execAsync = promisify(exec);

export async function POST(req: Request) {
  try {
    const { filepath } = await req.json();
    
    // Execute Python script
    const { stdout, stderr } = await execAsync(`python ../../backend/GE Automatic Email Tracking.py ${filepath}`);
    
    if (stderr) {
      return NextResponse.json({ error: stderr }, { status: 500 });
    }
    
    return NextResponse.json({ result: stdout });
  } catch (error) {
    console.error('Error executing Python script:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}