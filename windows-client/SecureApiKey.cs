using CredentialManagement;
namespace ExoAgente.Windows;
public static class SecureApiKey {
    public static string? Read(string target) {
        using var credential = new Credential { Target = target, Type = CredentialType.Generic, PersistanceType = PersistanceType.LocalComputer };
        return credential.Load() ? credential.Password : null;
    }
}
