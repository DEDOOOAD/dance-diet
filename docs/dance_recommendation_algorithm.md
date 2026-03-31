# Dance Recommendation Algorithm Draft

## Goal

Create a simple recommendation algorithm for our dance app without starting from full ML.

Use a rule-based score first:

- easy to implement
- easy to debug
- easy to tune later

## Simple Flow

```text
user behavior
  -> collect candidates
  -> score candidates
  -> apply diversity/fatigue rules
  -> return top dances for home feed
```

## Candidate Sources

Start with a small set of candidate pools:

- dances in the user's preferred genres
- dances similar to recently completed sessions
- dances from creators the user watches often
- trending dances
- dances near the user's current skill level

## Core Signals

Use simple weighted signals.

| signal | meaning | sample weight |
|---|---|---:|
| `genre_match` | user often watches this genre | `+4` |
| `skill_fit` | difficulty matches recent pose/completion level | `+3` |
| `liked_similar` | user liked or saved similar dances | `+3` |
| `creator_affinity` | user often watches this creator | `+2` |
| `recent_completion_similarity` | similar to dances user recently completed | `+2` |
| `trending` | currently popular content | `+1` |
| `social_boost` | friend or crew activity on this dance, optional | `+2` |
| `recent_skip` | user recently skipped similar content | `-4` |
| `difficulty_mismatch` | too hard or too easy | `-3` |
| `overexposed` | already shown too often | `-2` |

## Example Score Formula

```python
score = (
    4 * genre_match
    + 3 * skill_fit
    + 3 * liked_similar
    + 2 * creator_affinity
    + 2 * recent_completion_similarity
    + 1 * trending
    + 2 * social_boost
    - 4 * recent_skip
    - 3 * difficulty_mismatch
    - 2 * overexposed
)
```

Important note:

- `skill_fit` should be one of the strongest signals for a dance app
- this is more valuable than copying a social-media style "friend boost" directly

## Minimum Data Needed

### User-side

- recent views
- recent skips
- likes
- saves
- completion rate
- pose score or session accuracy
- favorite genre or repeated genre usage

### Content-side

- dance genre
- difficulty
- creator
- song or artist
- tags
- popularity or trend score

### Optional social data

- friend activity
- crew activity

## Good First Version

For V1, we do not need personalized model training.

We only need:

1. candidate generation
2. weighted score calculation
3. top-N sorting
4. simple diversity rule

Example diversity rule:

- do not show too many dances from the same artist or creator in a row

## Where It Can Plug In

Possible first integration point:

- generate recommended dances for the home feed
- later reuse the same scoring logic for classes or mission suggestions

In this project, the pose-related parts can reuse signals from the AI analysis server, while the final recommendation list can be returned from the general server.

## Future Upgrade Path

After enough usage data is collected:

- move weights into config
- tune weights with real user behavior
- learn weights automatically later
- split ranking into separate modes such as beginner, fitness, and trend-heavy

## Product Note

If ads or promoted content are added later, keep them separate from the organic recommendation score at first.

That makes the system easier to reason about and tune.
