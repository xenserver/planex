for m in planex-{fetch,patchqueue,depend}; do
  eval "$(register-python-argcomplete $m)"
done
