FROM node:22-bookworm-slim AS dependencies
WORKDIR /app/spring-boot-service
COPY spring-boot-service/package*.json ./
RUN npm ci --ignore-scripts
FROM node:22-bookworm-slim
WORKDIR /app/spring-boot-service
COPY --from=dependencies /app/spring-boot-service/node_modules ./node_modules
COPY spring-boot-service/scripts ./scripts
COPY spring-boot-service/contracts ./contracts
COPY spring-boot-service/src/main/resources/solidity ./src/main/resources/solidity
RUN mkdir -p /state /config && chown -R node:node /state /config /app
USER node
CMD ["node", "scripts/bridge-chain.cjs"]
