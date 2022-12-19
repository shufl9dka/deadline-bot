CREATE TABLE IF NOT EXISTS public.users
(
    user_id numeric NOT NULL PRIMARY KEY,
    registered timestamp without time zone NOT NULL,
    lang_code text NOT NULL,
    timezone text NOT NULL
);

CREATE TABLE IF NOT EXISTS public.deadlines
(
    deadline_id serial,
    user_id numeric NOT NULL,
    title text NOT NULL,
    deadline timestamp without time zone NOT NULL,
    repeat_in integer,
    remind_in integer,
    done boolean NOT NULL DEFAULT false,
    reminded boolean NOT NULL DEFAULT false
)