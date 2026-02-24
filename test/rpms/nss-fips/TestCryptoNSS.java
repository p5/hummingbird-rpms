import java.security.*;
import javax.crypto.*;

/**
 * Test Java crypto functionality explicitly using NSS PKCS11 provider.
 * This test requires the NSS libraries to be present and functional.
 */
public class TestCryptoNSS {
    public static void main(String[] args) throws Exception {
        System.out.println("Testing Java crypto with NSS PKCS11 provider...");

        // Configure NSS PKCS11 provider
        String nssConfig = 
            "name = NSS\n" +
            "nssLibraryDirectory = /usr/lib64\n" +
            "nssDbMode = noDb\n" +
            "attributes = compatibility\n";

        // Create a temporary config file
        java.io.File configFile = java.io.File.createTempFile("nss", ".cfg");
        configFile.deleteOnExit();
        java.io.FileWriter writer = new java.io.FileWriter(configFile);
        writer.write(nssConfig);
        writer.close();

        System.out.println("NSS config file: " + configFile.getAbsolutePath());

        // Load the SunPKCS11 provider with NSS configuration
        Provider nssProvider = Security.getProvider("SunPKCS11");
        if (nssProvider == null) {
            throw new RuntimeException("SunPKCS11 provider not available");
        }

        // Configure the provider with NSS
        Provider configuredProvider = nssProvider.configure(configFile.getAbsolutePath());
        Security.insertProviderAt(configuredProvider, 1);
        System.out.println("NSS PKCS11 provider loaded: " + configuredProvider.getName());

        // Test MessageDigest (SHA-256) using NSS provider
        MessageDigest md = MessageDigest.getInstance("SHA-256", configuredProvider);
        byte[] hash = md.digest("test data".getBytes());
        System.out.println("SHA-256 hash computed successfully via NSS");

        // Test KeyGenerator (AES) using NSS provider
        KeyGenerator kg = KeyGenerator.getInstance("AES", configuredProvider);
        kg.init(256);
        SecretKey sk = kg.generateKey();
        System.out.println("AES-256 key generated successfully via NSS");

        // Test Cipher (AES encryption) using NSS provider
        Cipher cipher = Cipher.getInstance("AES/CBC/PKCS5Padding", configuredProvider);
        cipher.init(Cipher.ENCRYPT_MODE, sk);
        byte[] encrypted = cipher.doFinal("test data".getBytes());
        System.out.println("AES-256 encryption successful via NSS");

        // Test Cipher (AES decryption) using NSS provider
        cipher.init(Cipher.DECRYPT_MODE, sk, cipher.getParameters());
        byte[] decrypted = cipher.doFinal(encrypted);
        System.out.println("AES-256 decryption successful via NSS");

        // Verify round-trip
        if (new String(decrypted).equals("test data")) {
            System.out.println("Round-trip encryption/decryption verified");
        } else {
            throw new RuntimeException("Decryption did not match original data!");
        }

        System.out.println("PASS: Java crypto works correctly with NSS PKCS11 provider");
    }
}
