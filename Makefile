# build delegates to just build, which runs frontend-build, then
# uv build --sdist and uv build --wheel as separate commands.
.DEFAULT_GOAL := ci
.PHONY: %
%:
	@AI="$(AI)" OUT="$(OUT)" REGEN_ROOT="$(REGEN_ROOT)" SHA="$(SHA)" \
	HF_LAYOUT_FORK="$(HF_LAYOUT_FORK)" BUMP="$(BUMP)" TEST="$(TEST)" \
	K="$(K)" PYTHON_VERSION="$(PYTHON_VERSION)" just $@
