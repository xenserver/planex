Planex demo walkthrough
-----------------------

Planex has two main goals - building SRPMs, and building RPMs. 

The first of this, generate SRPMs, is done from template spec
files and SCM repositories, generating appropriate version strings for
inclusion in the generated spec files from the
repositories. This functionality is in the executable 'planex-configure'. For
convenience, this utility will also generate SRPMs from plain spec files,
downloading whatever sources are necessary.

The second phase is assembling those SRPMs into binary RPMs. This is done
via mock, and will correctly order the builds such that dependencies are
satisfied, and can use an RPM-level cache in order to speed up overall build times. 

As an example of the functionality, there is a demo configuration directory
included with this repository - planex-demo.

Demo
----

The planex demo directory has two spec files within it, dumb.spec.in and
dumber.spec. The former is a template spec file that planex-configure will
modify in order to produce the final spec file. By contrast, dumber.spec 
is usable as it is, and all planex-configure will do is download the source
tarball from github.

First, make a scratch space in which the build will take place:


    mkdir planex-demo-workspace
    cd planex-demo-workspace


The reasoning behind referencing a git repository in the spec file is because
you plan on building something you're developing, so the next step is to 
clone the 'dumb' repository locally:


    git clone git://github.com/jonludlam/dumb


Now, we need a mock configuration, which is located within the planex-demo
directory:


    cp -r <planex-repository-location>/planex-demo/mock .


Unfortunately the mock configuration file needs to reference the absolute
path in which the RPMs will live, so that dependencies among the planex
spec files can be satisfied. Sed will do the trick for us:


    sed -i s+@LOCAL_RPMS_PATH@+file://`pwd`/planex-build-root/RPMS+ mock/default.cfg


Now, execute planex-configure:


    planex-configure --config-dir=<planex-repository-location>/planex-demo


At this point, the directory 'planex-build-root/SRPMS' will now contain
the two SRPMs for dumb and dumber:


    $ ls planex-build-root/SRPMS/
    dumb-0.1-1.src.rpm  dumber-0.0.1-1.src.rpm


At this point, we can now execute 'planex-build' which will build
the two RPMs. Note that because 'dumber' depends upon 'dumb', 'dumb'
will be built first.

Enable the cache
----------------

To speed things up a bit, lets enable the cache of RPMs. To do that,
planex just requires that you create the directory:


    mkdir rpmcache


Run planex-build again, and then again. The last time it is run,
it will just copy files from the cache rather than actually build them.

Make a change
-------------

Lets now make a change to the source of 'dumb'. Lets bump the version.
Change directory into the checkout of 'dumb' and we'll use sed to fix
the version:


    sed -i s/0.1/0.2/ VERSION


Commit the change (planex uses git archive, so changes must be committed
to work). Cd back up to our workspace, and now we need to recreate the new SRPMs, so execute configure,
then build:


    planex-configure --config-dir=<planex-repository-location>/planex-demo
    planex-build




