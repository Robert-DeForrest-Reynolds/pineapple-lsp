import * as vscode from 'vscode';
import * as cp from 'child_process';
import { LanguageClient, LanguageClientOptions, StreamInfo } from 'vscode-languageclient/node';
import * as path from 'path';


let client: LanguageClient;

export function activate(context: vscode.ExtensionContext) {

    // Server options using StreamInfo for stdio communication
    const serverOptions = (): Promise<StreamInfo> => {

        const pythonPath = process.platform === "win32"
        ? path.join(context.extensionPath, ".venv", "Scripts", "python.exe")
        : path.join(context.extensionPath, ".venv", "bin", "python");
        const serverPath = path.join(context.extensionPath, "server", "pineapple-lsp.py");
        console.log(pythonPath);
        console.log(serverPath);


        const output = vscode.window.createOutputChannel("Pineapple LSP");
        output.show(true);
        
        const childProcess = cp.spawn(pythonPath, [serverPath]);
        childProcess.on('exit', (code, signal) => {
            console.error(`Pineapple LSP exited with code ${code}, signal ${signal}`);
        });

        childProcess.stdout.on('data', (data: Buffer) => {
            console.log(`Pineapple LSP stdout: ${data.toString()}`);
            output.appendLine(`stdout: ${data.toString()}`);
        });

        childProcess.stderr.on('data', (data: Buffer) => {
            console.error(`Pineapple LSP stderr: ${data.toString()}`);
            output.appendLine(`stderr: ${data.toString()}`);
        });


        return Promise.resolve<StreamInfo>({
            reader: childProcess.stdout,
            writer: childProcess.stdin
        });
    };

    // Client options for VSCode
    const clientOptions: LanguageClientOptions = {
        documentSelector: [{ scheme: 'file', language: 'pineapple' }],
        synchronize: {
            // Watch for changes in Pineapple files
            fileEvents: vscode.workspace.createFileSystemWatcher('**/*.pineapple')
        }
    };

    // Create the language client
    client = new LanguageClient(
        'pineapple',
        'pineapple',
        serverOptions,
        clientOptions
    );

    // Start the client
    client.start();
}

export function deactivate(): Thenable<void> | undefined {
    if (!client) { return undefined; }
    return client.stop();
}
