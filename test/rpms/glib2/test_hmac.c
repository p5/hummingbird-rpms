/*
 * Verify that GLib's GHmac API is disabled for FIPS compliance.
 *
 * g_hmac_new() must always return NULL, and the convenience wrappers
 * (g_compute_hmac_for_data, g_compute_hmac_for_string, etc.) must
 * also return NULL since they delegate to g_hmac_new() internally.
 */
#include <glib.h>
#include <stdio.h>
#include <string.h>

static int failures = 0;

static void
expect_null(const char *test_name, const void *ptr)
{
    if (ptr != NULL) {
        fprintf(stderr, "FAIL [%s]: expected NULL, got non-NULL pointer\n", test_name);
        failures++;
    } else {
        printf("PASS: %s\n", test_name);
    }
}

/*
 * Test 1: g_hmac_new must return NULL
 */
static void
test_hmac_new_returns_null(void)
{
    /* Suppress the expected g_warning from the stub */
    g_log_set_handler("GLib", G_LOG_LEVEL_WARNING, (GLogFunc)g_log_default_handler, NULL);

    GHmac *hmac;

    hmac = g_hmac_new(G_CHECKSUM_SHA256,
                      (const guchar *)"key", 3);
    expect_null("g_hmac_new(SHA256) returns NULL", hmac);

    hmac = g_hmac_new(G_CHECKSUM_SHA1,
                      (const guchar *)"key", 3);
    expect_null("g_hmac_new(SHA1) returns NULL", hmac);

    hmac = g_hmac_new(G_CHECKSUM_SHA384,
                      (const guchar *)"key", 3);
    expect_null("g_hmac_new(SHA384) returns NULL", hmac);

    hmac = g_hmac_new(G_CHECKSUM_SHA512,
                      (const guchar *)"key", 3);
    expect_null("g_hmac_new(SHA512) returns NULL", hmac);

    hmac = g_hmac_new(G_CHECKSUM_MD5,
                      (const guchar *)"key", 3);
    expect_null("g_hmac_new(MD5) returns NULL", hmac);
}

/*
 * Test 2: g_compute_hmac_for_string must return NULL
 */
static void
test_compute_hmac_for_string_returns_null(void)
{
    gchar *result = g_compute_hmac_for_string(
        G_CHECKSUM_SHA256,
        (const guchar *)"Jefe", 4,
        "what do ya want for nothing?", -1);
    expect_null("g_compute_hmac_for_string returns NULL", result);
}

/*
 * Test 3: g_compute_hmac_for_data must return NULL
 */
static void
test_compute_hmac_for_data_returns_null(void)
{
    const guchar data[] = "test data";
    gchar *result = g_compute_hmac_for_data(
        G_CHECKSUM_SHA256,
        (const guchar *)"key", 3,
        data, sizeof(data) - 1);
    expect_null("g_compute_hmac_for_data returns NULL", result);
}

/*
 * Test 4: g_compute_hmac_for_bytes must return NULL
 */
static void
test_compute_hmac_for_bytes_returns_null(void)
{
    GBytes *key = g_bytes_new("key", 3);
    GBytes *data = g_bytes_new("test data", 9);
    gchar *result = g_compute_hmac_for_bytes(G_CHECKSUM_SHA256, key, data);
    expect_null("g_compute_hmac_for_bytes returns NULL", result);
    g_bytes_unref(key);
    g_bytes_unref(data);
}

int main(void) {
    test_hmac_new_returns_null();                /* Tests 1a-1e */
    test_compute_hmac_for_string_returns_null();  /* Test 2 */
    test_compute_hmac_for_data_returns_null();    /* Test 3 */
    test_compute_hmac_for_bytes_returns_null();   /* Test 4 */

    printf("\n%d test(s) failed\n", failures);
    return failures > 0 ? 1 : 0;
}
