/*
# SPDX-License-Identifier: LGPL-2.1+
# ~~~
#   Description: libcap tests
#
#   Author: Susant Sahani <susant@redhat.com>
#   Copyright (c) 2018 Red Hat, Inc.
# ~~~
*/
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <netinet/in.h>
#include <setjmp.h>
#include <inttypes.h>
#include <cmocka.h>
#include <sys/capability.h>
#include <netdb.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <errno.h>
#include <unistd.h>

void drop_cap(cap_value_t capflag) {
        cap_t d;

        d = cap_get_proc();
        assert_non_null(d);

        assert_return_code(cap_set_flag(d, CAP_EFFECTIVE, 1, &capflag, CAP_CLEAR), 0);
        assert_return_code(cap_set_flag(d, CAP_PERMITTED, 1, &capflag, CAP_CLEAR), 0);
        assert_return_code(cap_set_proc(d), 0);
}

void test_drop_cap_net_raw(void **state) {
        int s;

        assert_true((s = socket(AF_INET, SOCK_RAW, IPPROTO_UDP)) >= 0);
        close(s);

        drop_cap(CAP_NET_RAW);

        assert_false((s = socket(PF_INET, SOCK_RAW, IPPROTO_UDP)) >= 0);
}

int main(int argc, char *argv[]) {
        const struct CMUnitTest libcap_tests[] = {
                                                  cmocka_unit_test(test_drop_cap_net_raw),
        };

        return cmocka_run_group_tests(libcap_tests, NULL, NULL);
}
