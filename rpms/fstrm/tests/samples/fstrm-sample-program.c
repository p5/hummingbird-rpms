#include <fstrm.h>
#include <stdio.h>
#include <stdlib.h>

int
main(void)
{
	const char *file_path = "/tmp/output.fs";
	struct fstrm_file_options *fopt;
	struct fstrm_iothr *iothr;
	struct fstrm_writer *writer;

	fopt = fstrm_file_options_init();
	fstrm_file_options_set_file_path(fopt, file_path);
	writer = fstrm_file_writer_init(fopt, NULL);
	if (!writer) {
		fprintf(stderr, "Error: fstrm_file_writer_init() failed.\n");
		exit(EXIT_FAILURE);
	}

	iothr = fstrm_iothr_init(NULL, &writer);
	if (!iothr) {
		fprintf(stderr, "Error: fstrm_iothr_init() failed.\n");
		exit(EXIT_FAILURE);
	}

	fstrm_iothr_destroy(&iothr);
	fstrm_file_options_destroy(&fopt);

	return 0;
}
