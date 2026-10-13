FROM maven:3.9-eclipse-temurin-17 AS build
WORKDIR /app
COPY spring-boot-service/pom.xml ./
RUN mvn -B dependency:go-offline
COPY spring-boot-service/src ./src
RUN mvn -B package -DskipTests
FROM eclipse-temurin:17-jre-jammy
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/* && groupadd --gid 1000 foliolet && useradd --uid 1000 --gid 1000 --create-home foliolet && mkdir /state && chown foliolet:foliolet /state
WORKDIR /app
COPY --from=build /app/target/dms-*.jar app.jar
COPY containers/backend-entrypoint.sh /entrypoint.sh
USER foliolet
ENTRYPOINT ["sh", "/entrypoint.sh"]
