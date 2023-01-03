Create Table friends(
  friendCode text NOT NULL UNIQUE,
  online boolean NOT NULL,
  titleID text NOT NULL,
  updID text NOT NULL,
  lastAccessed bigint NOT NULL,
  username text,
  message text
);

Create Table config(
  BACKEND_UPTIME bigint NOT NULL
);
