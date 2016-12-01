for m in planex-{cache,fetch,patchqueue,depend}; do
  eval "$(register-python-argcomplete $m)"
done
