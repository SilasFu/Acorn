FROM eclipse-temurin:{{java_version}}-jdk AS builder
WORKDIR /app
COPY . .
{{#if build_tool}}
  {{#if maven}}RUN ./mvnw package -DskipTests{{/if}}
  {{#if gradle}}RUN ./gradlew build -x test{{/if}}
{{/if}}

FROM eclipse-temurin:{{java_version}}-jre
COPY --from=builder /app/target/*.jar /app.jar
EXPOSE {{port}}
CMD ["java", "-jar", "/app.jar"]
