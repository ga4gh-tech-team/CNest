Nothing:
	@echo "No target provided. Stop"

.PHONY: docker-build
docker-build:
	docker build -t ga4gh/cnest:0.1.0 .

.PHONY: docker-publish
docker-publish:
	docker image push ga4gh/cnest:0.1.0
