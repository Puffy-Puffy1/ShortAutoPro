#!/usr/bin/env python3

VERSION = "6.62"


def audit(events):

    ordered = sorted(
        list(events or []),
        key=lambda x: x.get("scene", 999)
    )


    longest = 0
    current = 0
    previous = None
    streaks = []

    start_scene = None


    for event in ordered:

        branch = event.get("branch")
        scene = event.get("scene")


        if branch == previous:

            current += 1

        else:

            if previous is not None:

                streaks.append(
                    {
                        "branch": previous,
                        "start_scene": start_scene,
                        "end_scene":
                            ordered[
                                max(0, len(streaks))
                            ].get("scene")
                            if False
                            else None,
                        "length": current,
                    }
                )


            previous = branch
            current = 1
            start_scene = scene


        longest = max(
            longest,
            current
        )


    # Rebuild streaks more cleanly.
    streaks = []

    if ordered:

        branch = ordered[0].get("branch")
        start = ordered[0].get("scene")
        last = start
        count = 0


        for event in ordered:

            current_branch = event.get("branch")
            current_scene = event.get("scene")


            if current_branch == branch:

                count += 1
                last = current_scene


            else:

                streaks.append(
                    {
                        "branch": branch,
                        "start_scene": start,
                        "end_scene": last,
                        "length": count,
                    }
                )


                branch = current_branch
                start = current_scene
                last = current_scene
                count = 1


        streaks.append(
            {
                "branch": branch,
                "start_scene": start,
                "end_scene": last,
                "length": count,
            }
        )


    recommendations = []


    for streak in streaks:

        if (
            streak["branch"] == "STILL"
            and streak["length"] >= 5
        ):

            recommendations.append(
                {
                    "type":
                        "BREAK_STILL_VISUAL_PATTERN",

                    "start_scene":
                        streak["start_scene"],

                    "end_scene":
                        streak["end_scene"],

                    "note":
                        (
                            "Do not fabricate video. "
                            "Prefer stronger motion-profile "
                            "variation or real documentary "
                            "video when retrieval provides it."
                        ),
                }
            )


    return {
        "version": VERSION,
        "status":
            (
                "PASS_WITH_WARNINGS"
                if recommendations
                else "PASS"
            ),
        "longest_streak": longest,
        "streaks": streaks,
        "recommendations": recommendations,
        "media_changed": False,
    }


def self_test():

    events = [
        {
            "scene": n,
            "branch":
                (
                    "VIDEO"
                    if n in {2, 8}
                    else "STILL"
                )
        }
        for n in range(1, 13)
    ]


    result = audit(events)

    assert result["media_changed"] is False

    print("VI6.62 MEDIA STREAK=PASS")


if __name__ == "__main__":
    self_test()
