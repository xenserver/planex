for m in planex-{cache,fetch,depend}; do
  eval "$(register-python-argcomplete $m)"
done
