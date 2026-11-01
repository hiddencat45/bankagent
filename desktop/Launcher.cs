using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;
using System.Reflection;

[assembly: AssemblyTitle("Youdu")]
[assembly: AssemblyProduct("Youdu - local banking assistant")]
[assembly: AssemblyVersion("1.0.0.0")]

internal static class Launcher
{
    [STAThread]
    private static int Main()
    {
        string root = AppDomain.CurrentDomain.BaseDirectory;
        string python = Path.Combine(root, @".venv\Scripts\pythonw.exe");
        string app = Path.Combine(root, @"desktop\app.py");
        if (!File.Exists(python) || !File.Exists(app))
        {
            MessageBox.Show("请将 Youdu.exe 放在项目根目录，并先运行 scripts/setup-desktop.ps1。",
                "有度 · 启动环境不完整", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
        try
        {
            var start = new ProcessStartInfo {
                FileName = python,
                Arguments = "\"" + app + "\"",
                WorkingDirectory = root,
                UseShellExecute = false,
                CreateNoWindow = true
            };
            // Optional per-install binding overrides inherited/registry ledger settings.
            // Never silently create a replacement when an explicitly bound file is missing.
            string binding = Path.Combine(root, "Youdu.ledger-path");
            if (File.Exists(binding))
            {
                string ledger = File.ReadAllText(binding).Trim();
                if (!Path.IsPathRooted(ledger) || !File.Exists(ledger))
                {
                    MessageBox.Show("已绑定的账本不存在或路径无效。请检查 Youdu.ledger-path，恢复原文件后重试。\n不会改用其他账本或创建空账本。",
                        "有度 · 账本不可用", MessageBoxButtons.OK, MessageBoxIcon.Error);
                    return 1;
                }
                start.EnvironmentVariables["BANKAGENT_DB_PATH"] = Path.GetFullPath(ledger);
            }
            Process.Start(start);
            return 0;
        }
        catch
        {
            MessageBox.Show("无法启动本地应用。请检查项目路径和 Python 环境。",
                "有度 · 启动失败", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
    }
}
