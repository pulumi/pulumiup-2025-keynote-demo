# Initech Compliance Policy Pack

This contains two policies:

* `"check-required-tags"`: checks for all known taggable resource types and ensures they have proper tags. The `"requiredTags"` configuration parameter is an optional `string[]` that lets an organization configure which tags to enforce.

* `"disallow-massive-ecs-tasks"`: disallows ECS tasks with CPU and/or memory that exceeds thresholds. The configuration parameters `"maxCpu"` and `"maxMemory"` are optional integers and represent the max thresholds.

You can test it out locally by running `pulumi up --policy-pack /path/to/this/pack --policy-pack-config ./config.json`, where `config.json` looks something like this:

```json
{
    "check-required-tags": {
        "requiredTags": [ "Department" ]
    },
    "disallow-massive-ecs-tasks": {
        "maxCpu": 64,
        "maxMemory": 64
    }
}
```

Even better is to use organizational policy enforcement.
