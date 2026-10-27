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
            Process.Start(new ProcessStartInfo {
                FileName = python,
                Arguments = "\"" + app + "\"",
                WorkingDirectory = root,
                UseShellExecute = false,
                CreateNoWindow = true
            });
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
