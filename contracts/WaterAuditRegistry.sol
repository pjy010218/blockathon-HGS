// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title Water Audit Registry
/// @notice Stores the existence and timestamp of a source-record digest.
///         The source payload stays off-chain; the digest makes later changes detectable.
contract WaterAuditRegistry {
    struct Anchor {
        uint64 anchoredAt;
        address submitter;
        string source;
        string sourceRecordId;
    }

    mapping(bytes32 => Anchor) private anchors;

    event RecordAnchored(
        bytes32 indexed recordHash,
        uint64 anchoredAt,
        address indexed submitter,
        string source,
        string sourceRecordId
    );

    function anchorRecord(
        bytes32 recordHash,
        string calldata source,
        string calldata sourceRecordId
    ) external {
        require(recordHash != bytes32(0), "empty record hash");
        require(anchors[recordHash].anchoredAt == 0, "record already anchored");

        uint64 timestamp = uint64(block.timestamp);
        anchors[recordHash] = Anchor(timestamp, msg.sender, source, sourceRecordId);
        emit RecordAnchored(recordHash, timestamp, msg.sender, source, sourceRecordId);
    }

    function getAnchor(bytes32 recordHash) external view returns (Anchor memory) {
        return anchors[recordHash];
    }
}
