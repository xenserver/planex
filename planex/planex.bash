for m in planex-{cache,fetch,pin,depend}; do
  eval "$(register-python-argcomplete $m)"
done
