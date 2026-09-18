using System.Diagnostics;
using System.Net.Http;
using System.Net.Http.Json;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Navigation;
namespace ExoAgente.Windows;
public partial class MainWindow : Window {
    private readonly HttpClient client = new();
    private readonly HashSet<string> knownWaitingMerge = new();
    private bool hasLoadedWaitingMerge;
    private const string CredentialTarget = "ExoAgenteCI.BackendApiKey";
    public MainWindow() { InitializeComponent(); var apiKey = SecureApiKey.Read(CredentialTarget); if (!string.IsNullOrWhiteSpace(apiKey)) client.DefaultRequestHeaders.Add("X-API-Key", apiKey); }
    private string Base => BackendUrl.Text.TrimEnd('/');
    private async void Window_Loaded(object sender, RoutedEventArgs e) => await RefreshAsync();
    private async void Refresh_Click(object sender, RoutedEventArgs e) => await RefreshAsync();
    private async void StatusFilter_Changed(object sender, SelectionChangedEventArgs e) { if (IsLoaded) await RefreshFindingsAsync(); }
    private string? SelectedStatus() => (StatusFilter.SelectedItem as ComboBoxItem)?.Content?.ToString() is string value && value != "Todos" ? value : null;
    private async Task RefreshAsync() {
        try { JobsGrid.ItemsSource = await client.GetFromJsonAsync<List<Dictionary<string, object>>>($"{Base}/jobs"); await RefreshFindingsAsync(); var waiting = await client.GetFromJsonAsync<List<Dictionary<string, object>>>($"{Base}/findings?status=aguardando_merge") ?? new(); PrGrid.ItemsSource = waiting; var currentIds = waiting.Where(item => item.TryGetValue("id", out _)).Select(item => item["id"].ToString()!).ToHashSet(); var newCount = hasLoadedWaitingMerge ? currentIds.Except(knownWaitingMerge).Count() : 0; knownWaitingMerge.Clear(); knownWaitingMerge.UnionWith(currentIds); hasLoadedWaitingMerge = true; if (newCount > 0) WindowsNotifier.NewWaitingMerge(newCount); var scope = await client.GetFromJsonAsync<JsonElement>($"{Base}/scope"); ScopeJson.Text = JsonSerializer.Serialize(scope, new JsonSerializerOptions { WriteIndented = true }); }
        catch (Exception ex) { WindowsNotifier.JobFailed(ex.Message); MessageBox.Show(ex.Message, "Erro ao carregar backend"); }
    }
    private async Task RefreshFindingsAsync() {
        var suffix = SelectedStatus() is string status ? $"?status={Uri.EscapeDataString(status)}" : "";
        FindingsGrid.ItemsSource = await client.GetFromJsonAsync<List<Dictionary<string, object>>>($"{Base}/findings{suffix}");
    }
    private async void SaveScope_Click(object sender, RoutedEventArgs e) {
        try { using var content = JsonContent.Create(JsonSerializer.Deserialize<JsonElement>(ScopeJson.Text)); var response = await client.PutAsync($"{Base}/scope", content); response.EnsureSuccessStatusCode(); await RefreshAsync(); MessageBox.Show("Escopo salvo."); }
        catch (Exception ex) { WindowsNotifier.JobFailed(ex.Message); MessageBox.Show(ex.Message, "Erro ao salvar escopo"); }
    }
    private void PrLink_RequestNavigate(object sender, RequestNavigateEventArgs e) { Process.Start(new ProcessStartInfo(e.Uri.AbsoluteUri) { UseShellExecute = true }); e.Handled = true; }
}
