#include <stdio.h>
#include <unicode/utypes.h>
#include <unicode/unistr.h>
#include <unicode/calendar.h>
#include <unicode/ustdio.h>
#include <unicode/datefmt.h>
#include <unicode/locid.h>

using namespace icu;

int fail_count = 0;
int pass_count = 0;

void test_dst(const char *timezone,
              int year,
              int month,
              int day,
              int hour,
              int minute,
              int second,
              int std_offset_hours_expected,
              int dst_offset_hours_expected) {
    UErrorCode success = U_ZERO_ERROR;
    UnicodeString dateReturned, curTZNameEn, curTZNameJp;
    UDate dateTime;
    int32_t stdOffset, dstOffset;
    int std_offset_hours, dst_offset_hours;

    TimeZone *tz = TimeZone::createTimeZone(timezone);

    curTZNameEn = tz->getDisplayName(Locale::getEnglish(), curTZNameEn);
    u_printf("%s-name-english=%S\n",
             timezone,
             curTZNameEn.getTerminatedBuffer());

    curTZNameJp = tz->getDisplayName(Locale::getJapanese(), curTZNameJp);
    u_printf("%s-name-japanese=%S\n",
             timezone,
             curTZNameJp.getTerminatedBuffer());

    Calendar *calendar = Calendar::createInstance(success);
    calendar->adoptTimeZone(TimeZone::createTimeZone("UTC"));

    DateFormat *dt = DateFormat::createDateTimeInstance(
        DateFormat::LONG, DateFormat::LONG, Locale("ja", "JP"));
    dt->adoptTimeZone(TimeZone::createTimeZone("UTC"));

    // Set time in UTC, note that month is from 0-11.
    calendar->set(year, month, day, hour, minute, second);
    dateTime = calendar->getTime(success);
    dateReturned = "";
    dateReturned = dt->format(dateTime, dateReturned, success);
    printf("current-time-utc-%4d-%d-%d-%d-%d-%d=",
           year, month, day, hour, minute, second);
    u_printf("%S\n", dateReturned.getTerminatedBuffer());
    tz->getOffset(dateTime, true, stdOffset, dstOffset, success);
    std_offset_hours = stdOffset/(1000*60*60);
    dst_offset_hours = dstOffset/(1000*60*60);

    printf("%s-std-offset-%4d-%d-%d-%d-%d-%d=%d\n",
           timezone,
           year, month, day, hour, minute, second,
           std_offset_hours);

    if (std_offset_hours != std_offset_hours_expected) {
        printf("std_offset_hours=%d, std_offset_hours_expected=%d\n",
               std_offset_hours, std_offset_hours_expected);
        printf("FAIL\n");
        fail_count++;
    }
    else {
        printf("PASS\n");
        pass_count++;
    }

    printf("%s-dst-offset-%4d-%d-%d-%d-%d-%d=%d\n",
           timezone,
           year, month, day, hour, minute, second,
           dst_offset_hours);

    if (dst_offset_hours != dst_offset_hours_expected) {
        printf("dst_offset_hours=%d, dst_offset_hours_expected=%d\n",
               dst_offset_hours, dst_offset_hours_expected);
        printf("FAIL\n");
        fail_count++;
    }
    else {
        printf("PASS\n");
        pass_count++;
    }

    delete calendar;
    delete dt;
    delete tz;
}

int main(int argc, char** argv) {

    // zdump -c 2019,2020 -v Asia/Gaza
    // Asia/Gaza  Fri Oct 25 20:59:59 2019 UT = Fri Oct 25 23:59:59 2019 EEST isdst=1 gmtoff=10800
    // Asia/Gaza  Fri Oct 25 21:00:00 2019 UT = Fri Oct 25 23:00:00 2019 EET isdst=0 gmtoff=7200

    // timezone, year, month (0-11), day, hour, minute, second,
    // std offset expected, dst offset expected:
    test_dst("Asia/Gaza", 2019, 9, 25, 20, 59, 59, 2, 1);
    // Why doesn’t this work with the exactly correct time?:
    test_dst("Asia/Gaza", 2019, 9, 25, 21, 0, 0, 2, 1); // wrong!
    test_dst("Asia/Gaza", 2019, 9, 25, 23, 0, 0, 2, 0);

    // Asia/Gaza  Fri Oct 23 21:59:59 2020 UT = Sat Oct 24 00:59:59 2020 EEST isdst=1 gmtoff=10800
    // Asia/Gaza  Fri Oct 23 22:00:00 2020 UT = Sat Oct 24 00:00:00 2020 EET isdst=0 gmtoff=7200
    test_dst("Asia/Gaza", 2020, 9, 23, 21, 59, 59, 2, 1);
    test_dst("Asia/Gaza", 2020, 9, 23, 22, 0, 0, 2, 1); // wrong!
    test_dst("Asia/Gaza", 2020, 9, 24, 22, 0, 0, 2, 0);

    // Asia/Gaza  Thu Oct 28 21:59:59 2021 UT = Fri Oct 29 00:59:59 2021 EEST isdst=1 gmtoff=10800
    // Asia/Gaza  Thu Oct 28 22:00:00 2021 UT = Fri Oct 29 00:00:00 2021 EET isdst=0 gmtoff=7200

    test_dst("Asia/Gaza", 2021, 9, 28, 21, 59, 59, 2, 1);
    test_dst("Asia/Gaza", 2021, 9, 28, 22, 0, 0, 2, 1); // wrong!
    test_dst("Asia/Gaza", 2021, 9, 29, 21, 59, 59, 2, 0);
    test_dst("Asia/Gaza", 2021, 9, 30, 22, 0, 0, 2, 0);

    // Print summary and exit with the number of failed test or
    // exit with 0 if all tests passed.
    printf("Summary: %d tests failed, %d tests passed.\n",
           fail_count, pass_count);
    if (fail_count != 0) {
        printf("FAIL\n");
        exit(fail_count);
    }
    printf("PASS\n");
    exit(0);
}
