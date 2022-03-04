Nothing:
	@echo "No target provided. Stop"

.PHONY: tar-rbin
tar-rbin:
	@cd src; tar -cf Rbin_1.2.tar.gz Rbin

.PHONY: docker-build
docker-build:
	@docker build -t ga4gh/cnest:0.1.0 .

.PHONY: docker-publish
docker-publish:
	@docker image push ga4gh/cnest:0.1.0
