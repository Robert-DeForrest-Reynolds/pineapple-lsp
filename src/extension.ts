import * as vscode from 'vscode';
import * as cp from 'child_process';
import * as fs from 'fs';
import * as path from 'path';
import { LanguageClient, LanguageClientOptions, StreamInfo } from 'vscode-languageclient/node';

let client: LanguageClient;

// Run a process and return when finished
function runAsync(command: string, args: string[], cwd?: string): Promise<void> {
    return new Promise((resolve, reject) => {
        const proc = cp.spawn(command, args, {
                              stdio: 'inherit',
                              cwd,
                              shell: true,
                              windowsHide: true
                              });  // <-- Add this});
        proc.on('error', reject);
        proc.on('exit', code => code === 0 ? resolve() : reject(new Error(`Process exited with ${code}`)));
    });
}

// Ensure venv and dependencies
async function ensureVenv(context: vscode.ExtensionContext): Promise<string> {
    const venvPath = path.join(context.extensionPath, '.venv');
    const pythonPath = process.platform === 'win32'
        ? path.join(venvPath, 'Scripts', 'python.exe')
        : path.join(venvPath, 'bin', 'python');

    if (!fs.existsSync(pythonPath)) {
        vscode.window.showInformationMessage('Creating Python venv for pineapple-lsp...');
        await runAsync('python', ['-m', 'venv', venvPath]);
    }

    // Upgrade pip and install dependencies
    await runAsync(pythonPath, ['-m', 'pip', 'install', '--upgrade', 'pip']);
    await runAsync(pythonPath, ['-m', 'pip', 'install', 'pygls==2.0.0a6']);

    return pythonPath;
}

export async function activate(context: vscode.ExtensionContext) {
    const serverOptions = async (): Promise<StreamInfo> => {
        const venvPath = path.join(context.extensionPath, '.venv');
        const pythonPath = await ensureVenv(context);
        const serverPath = path.join(context.extensionPath, 'server', 'pineapple-lsp.py');

        const output = vscode.window.createOutputChannel('Pineapple LSP');
        output.show(true);

        const childProcess = cp.spawn(pythonPath, [serverPath], {
            stdio: ['pipe', 'pipe', 'pipe'],
            cwd: context.extensionPath,
            env: { ...process.env },
            windowsHide: true   // <-- Add this
        });

        childProcess.stdout.on('data', (data: Buffer) => output.appendLine(data.toString()));
        childProcess.stderr.on('data', (data: Buffer) => output.appendLine(`ERROR: ${data.toString()}`));
        childProcess.on('exit', (code, signal) => {
            output.appendLine(`LSP exited with code ${code}, signal ${signal}`);
        });

        return { reader: childProcess.stdout, writer: childProcess.stdin };
    };

    const clientOptions: LanguageClientOptions = {
        documentSelector: [{ scheme: 'file', language: 'pineapple' }],
        synchronize: {
            fileEvents: vscode.workspace.createFileSystemWatcher('**/*.pineapple')
        }
    };

    client = new LanguageClient('pineapple', 'Pineapple LSP', serverOptions, clientOptions);
    await client.start();
}

export function deactivate(): Thenable<void> | undefined {
    if (!client) return undefined;
    return client.stop();
}
