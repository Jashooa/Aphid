CREATE USER aphid PASSWORD 'passwordgoeshere' LOGIN NOSUPERUSER;

CREATE DATABASE aphid OWNER aphid;

CREATE TABLE IF NOT EXISTS timers(
    "id" SERIAL PRIMARY KEY,
    "event" VARCHAR(16) NOT NULL,
    "expires" TIMESTAMP NOT NULL
);

ALTER TABLE timers OWNER TO aphid;

CREATE TABLE IF NOT EXISTS temproles(
    "user_id" BIGINT,
    "role_id" BIGINT,
    "timer_id" INTEGER REFERENCES timers("id") ON DELETE CASCADE,
    PRIMARY KEY ("user_id", "role_id")
);

ALTER TABLE temproles OWNER TO aphid;

CREATE TABLE IF NOT EXISTS temprole_whitelist(
    "role_id" BIGINT PRIMARY KEY
);

ALTER TABLE temprole_whitelist OWNER TO aphid;

CREATE TABLE IF NOT EXISTS stickymessages(
    "channel_id" BIGINT PRIMARY KEY,
    "last_message" BIGINT NOT NULL,
    "delay" FLOAT NOT NULL,
    "image_only" BOOLEAN NOT NULL,
    "content" VARCHAR(2000)
);

ALTER TABLE stickymessages OWNER TO aphid;

CREATE TABLE IF NOT EXISTS mod_cases(
    "id" SERIAL PRIMARY KEY,
    "action" VARCHAR(16),
    "user_id" BIGINT NOT NULL,
    "mod_id" BIGINT NOT NULL,
    "issued" TIMESTAMP NOT NULL,
    "duration" INTERVAL,
    "reason" VARCHAR(512)
);

ALTER TABLE mod_cases OWNER TO aphid;

CREATE TABLE IF NOT EXISTS mod_tempactions(
    "user_id" BIGINT,
    "action" VARCHAR(16),
    "timer_id" INTEGER REFERENCES timers("id") ON DELETE CASCADE,
    PRIMARY KEY ("user_id", "action")
);

ALTER TABLE mod_tempactions OWNER TO aphid;