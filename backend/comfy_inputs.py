"""Wire H3 reference groups in ComfyUI's dynamic-input API format."""

REFERENCE_GROUPS = ("ref_images", "ref_videos", "ref_video_audios", "ref_audios")


def prepare_comfy_inputs(workflow: dict) -> dict:
    """Flatten reference sockets before submission, preserving the caller graph.

    ComfyUI reconstructs Autogrow groups from dotted socket names. Sending a
    nested dictionary is accepted but reconstructs an empty reference group.
    """
    result = workflow.copy()
    for node_id, node in workflow.items():
        if node.get("class_type") != "MiniMaxH3ReferenceToVideo":
            continue
        inputs = node.get("inputs", {})
        groups = [name for name in REFERENCE_GROUPS if name in inputs]
        if not groups:
            continue
        inputs = inputs.copy()
        for group in groups:
            sockets = inputs.pop(group)
            if not isinstance(sockets, dict):
                raise ValueError(f"H3 reference group {group} must be a dictionary")
            for socket, value in sockets.items():
                name = f"{group}.{socket}"
                if name in inputs and inputs[name] != value:
                    raise ValueError(f"Conflicting H3 reference socket: {name}")
                inputs[name] = value
        result[node_id] = {**node, "inputs": inputs}
    return result
