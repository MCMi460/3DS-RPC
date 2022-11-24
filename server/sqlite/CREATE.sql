Create Table friends(
  friendCode text NOT NULL UNIQUE,
  online boolean NOT NULL,
  titleID text NOT NULL,
  updID text NOT NULL,
  lastAccessed bigint NOT NULL,
  notifications text,
  username text,
  message text
);

Create Table auth(
  friendCode text NOT NULL UNIQUE,
  token text UNIQUE,
  password text,
  tempAuth text UNIQUE
);
