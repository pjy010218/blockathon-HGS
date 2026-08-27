// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title Water Audit Registry
/// @notice Stores the existence and timestamp of a source-record digest.
///         The source payload stays off-chain; the digest makes later changes detectable.
contract WaterAuditRegistry {
    bytes32 public constant ROLE_COMMUNITY = "community";
    bytes32 public constant ROLE_GOVERNMENT = "government";

    struct Anchor {
        uint64 anchoredAt;
        address submitter;
        address attributedTo;
        bytes32 issuerRole;
        string source;
        string sourceRecordId;
    }

    address public immutable owner;

    mapping(address => bytes32) private issuerRoles;
    mapping(bytes32 => Anchor) private anchors;

    event IssuerRegistered(address indexed account, bytes32 indexed role);
    event IssuerRevoked(address indexed account, bytes32 indexed role);
    event RecordAnchored(
        bytes32 indexed recordHash,
        uint64 anchoredAt,
        address indexed submitter,
        address indexed attributedTo,
        bytes32 issuerRole,
        string source,
        string sourceRecordId
    );

    modifier onlyOwner() {
        require(msg.sender == owner, "caller is not the owner");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    /// @notice Allow an account to anchor records under a role.
    /// @dev Roles separate community and government submissions so one cannot be
    ///      passed off as the other. The role in force at anchoring time is stored
    ///      with the record, so a later revocation does not rewrite history.
    function registerIssuer(address account, string calldata role) external onlyOwner {
        require(account != address(0), "issuer address required");

        bytes32 encoded = _encodeRole(role);
        issuerRoles[account] = encoded;
        emit IssuerRegistered(account, encoded);
    }

    function revokeIssuer(address account) external onlyOwner {
        bytes32 role = issuerRoles[account];
        require(role != bytes32(0), "issuer is not registered");

        delete issuerRoles[account];
        emit IssuerRevoked(account, role);
    }

    function isIssuer(address account, string calldata role) external view returns (bool) {
        return issuerRoles[account] == _encodeRole(role);
    }

    function issuerRole(address account) external view returns (bytes32) {
        return issuerRoles[account];
    }

    /// @dev Roles are named in the public interface and stored as bytes32. The
    ///      two published constants show the encoding.
    function _encodeRole(string calldata role) private pure returns (bytes32) {
        bytes32 named = keccak256(bytes(role));
        if (named == keccak256("community")) return ROLE_COMMUNITY;
        if (named == keccak256("government")) return ROLE_GOVERNMENT;
        revert("unknown issuer role");
    }

    /// @notice One record to anchor, used by the batch entry point.
    struct RecordSubmission {
        bytes32 recordHash;
        string source;
        string sourceRecordId;
    }

    function anchorRecord(
        bytes32 recordHash,
        string calldata source,
        string calldata sourceRecordId
    ) external {
        _anchorRecord(recordHash, source, sourceRecordId, msg.sender);
    }

    /// @notice Anchor a record on behalf of the contributor who signed it.
    /// @dev For the relayed mode, where a service wallet sends the transaction
    ///      after verifying the contributor's signature off-chain. `submitter`
    ///      stays the relayer; `attributedTo` is the contributor, so credit
    ///      follows the signer rather than whoever paid the gas.
    function anchorRecordFor(
        bytes32 recordHash,
        string calldata source,
        string calldata sourceRecordId,
        address contributor
    ) external {
        require(contributor != address(0), "contributor address required");
        _anchorRecord(recordHash, source, sourceRecordId, contributor);
    }

    /// @notice Anchor many records in one transaction.
    /// @dev Ingesting a whole source run one transaction at a time is what makes
    ///      teams anchor only a filtered subset. This exists so anchoring
    ///      everything received stays practical, and the filtering that happens
    ///      afterwards stays visible rather than being baked into what the chain
    ///      ever saw.
    ///
    ///      All or nothing: if any record is empty or already anchored the whole
    ///      batch reverts, so there is never a partial run to reconcile. Screen a
    ///      batch with `getAnchors` first when re-running an ingestion.
    function anchorRecords(RecordSubmission[] calldata submissions) external {
        for (uint256 index = 0; index < submissions.length; index++) {
            _anchorRecord(
                submissions[index].recordHash,
                submissions[index].source,
                submissions[index].sourceRecordId,
                msg.sender
            );
        }
    }

    function _anchorRecord(
        bytes32 recordHash,
        string calldata source,
        string calldata sourceRecordId,
        address attributedTo
    ) private {
        bytes32 role = issuerRoles[msg.sender];
        require(role != bytes32(0), "caller is not a registered issuer");
        require(recordHash != bytes32(0), "empty record hash");
        require(anchors[recordHash].anchoredAt == 0, "record already anchored");

        uint64 timestamp = uint64(block.timestamp);
        anchors[recordHash] = Anchor(
            timestamp, msg.sender, attributedTo, role, source, sourceRecordId
        );
        emit RecordAnchored(
            recordHash, timestamp, msg.sender, attributedTo, role, source, sourceRecordId
        );
    }

    function getAnchor(bytes32 recordHash) external view returns (Anchor memory) {
        return anchors[recordHash];
    }

    /// @notice Whether a record hash has been anchored.
    /// @dev getAnchor returns a zeroed struct for an unknown hash rather than
    ///      reverting, and a zero address reads like a real answer. Use this when
    ///      the only question is whether the record exists on-chain.
    function isAnchored(bytes32 recordHash) external view returns (bool) {
        return anchors[recordHash].anchoredAt != 0;
    }

    /// @notice Read several anchors in one call.
    /// @dev For a map or list view that would otherwise make one request per
    ///      visible record. Results are returned in the order asked for, and an
    ///      unanchored hash yields a zeroed entry rather than being skipped, so
    ///      positions still line up with the input. Costs no gas; keep batches to
    ///      a size the RPC endpoint returns comfortably.
    function getAnchors(bytes32[] calldata recordHashes)
        external
        view
        returns (Anchor[] memory)
    {
        Anchor[] memory found = new Anchor[](recordHashes.length);
        for (uint256 index = 0; index < recordHashes.length; index++) {
            found[index] = anchors[recordHashes[index]];
        }
        return found;
    }
}
