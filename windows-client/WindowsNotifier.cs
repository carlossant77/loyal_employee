using Microsoft.Toolkit.Uwp.Notifications;
namespace ExoAgente.Windows;
public static class WindowsNotifier {
    public static void JobFailed(string message) => Show("Falha no Job CI/SonarQube", message);
    public static void NewWaitingMerge(int count) => Show("Pendência aguardando merge", $"Há {count} nova(s) pendência(s) aguardando merge.");
    private static void Show(string title, string body) => new ToastContentBuilder().AddText(title).AddText(body).Show();
}
