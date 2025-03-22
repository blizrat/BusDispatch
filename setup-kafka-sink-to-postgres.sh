curl -X PUT http://localhost:8083/connectors/sink-jdbc-postgres-01/config \
     -H "Content-Type: application/json" -d '{
    "connector.class"                    : "io.confluent.connect.jdbc.JdbcSinkConnector",
    "connection.url"                     : "jdbc:postgresql://postgres:5432/postgres",
    "topics"                             : "bus_topic_avro",
    "key.converter"                      : "org.apache.kafka.connect.storage.StringConverter",
    "value.converter"                    : "io.confluent.connect.avro.AvroConverter",
    "value.converter.schema.registry.url": "http://schema-registry:8081",
    "connection.user"                    : "postgres",
    "connection.password"                : "postgres",
    "auto.create"                        : true,
    "auto.evolve"                        : true,
    "insert.mode"                        : "insert",
    "pk.mode"                            : "record_value"
}'