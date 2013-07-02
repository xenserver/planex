#include <stdio.h>
#include <stdlib.h>
#include <rpm/rpmlib.h>
#include <rpm/rpmbuild.h>

/* usage: ./makemake <spec> <SRPM path> */
int main(int argc, char * argv[]) {
  rpmts ts = rpmtsCreate();
  char *specfile = argv[1];
  char *targetarch=NULL;
  void *pointer;
  int_32 data_size;
  int_32 type;
  int ret=0;
  Spec spec;
  Package pkg;
  const char *errorString;
  int noarch=0;
  int fst=0;
  const char *name, *version, *release, *epoch, *arch;

  if(argc>2) {
	targetarch=argv[3];
  }
  int status = rpmReadConfigFiles( (const char*) NULL,
				   targetarch);

  if (parseSpec(ts, specfile, NULL, NULL, 0, NULL, NULL, 0, 0)) {
    printf ("fail\n");
    exit(1);
  }

  if ((spec = rpmtsSetSpec(ts, NULL)) == NULL) {
    exit(1);
  }

  printf("{ \"srcrpm\":\"%s\",\n  \"packages\":[\n",argv[2]);
  for (pkg = spec->packages; pkg != NULL; pkg = pkg->next) {
    if (pkg->fileList == NULL)
      continue;

    headerNEVRA(pkg->header, &name, &epoch, &version, &release, &arch);
    const char *binFormat = "%{ARCH}";    
    char *binRpm = headerSprintf(pkg->header, binFormat, rpmTagTable,
                               rpmHeaderFormats, &errorString);
    if(strcmp(binRpm,"noarch")==0)
	noarch=1;
    if(fst==1)
	printf(",");
    else
	fst=1;
    printf("    {\"name\":\"%s\", \"version\":\"%s\", \"release\":\"%s\", \"noarch\":\"%d\", \"arch\":\"%s\"}",name,version,release,noarch,arch);
    
  }
      printf("]\n");

  printf("}\n");
  exit(0);
}

