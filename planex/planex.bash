for m in planex-{build-mock,clone-sources,depend,fetch,init,make-srpm,manifest,patchqueue}; do
  eval "$(register-python-argcomplete $m)"
done
