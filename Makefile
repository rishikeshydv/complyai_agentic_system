COMPOSE=docker compose -f infra/docker-compose.yml

up:
	$(COMPOSE) up --build

down:
	$(COMPOSE) down -v

logs:
	$(COMPOSE) logs -f

ps:
	$(COMPOSE) ps

trigger-aml:
	curl -X POST "http://localhost:8000/v1/alerts/ALERT-001/pull?bank_id=demo&sync=true"

trigger-sanctions:
	curl -X POST "http://localhost:8000/v1/alerts/ALERT-002/pull?bank_id=demo&sync=true"

poll-ingestion:
	curl -X POST "http://localhost:8000/v1/alerts/ingestion/poll"

playground-start:
	curl -X POST "http://localhost:8000/v1/playground/start" \
		-H "Content-Type: application/json" \
		-d '{"bank_id":"demo","seed_customers":20,"tx_per_tick":12,"aml_alert_rate":0.2,"sanctions_alert_rate":0.05}'

playground-tick:
	curl -X POST "http://localhost:8000/v1/playground/tick" \
		-H "Content-Type: application/json" \
		-d '{"bank_id":"demo","count":5,"run_ingestion_poll":true}'

playground-stop:
	curl -X POST "http://localhost:8000/v1/playground/stop?bank_id=demo"
