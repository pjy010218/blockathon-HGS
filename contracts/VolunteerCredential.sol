// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @notice The part of the record registry this credential reads.
/// @dev The struct must mirror WaterAuditRegistry.Anchor exactly so the return
///      data decodes correctly.
interface IWaterAuditRegistry {
    struct Anchor {
        uint64 anchoredAt;
        address submitter;
        address attributedTo;
        bytes32 issuerRole;
        string source;
        string sourceRecordId;
    }

    function getAnchor(bytes32 recordHash) external view returns (Anchor memory);
}

/// @title Volunteer Credential
/// @notice Recognition for contributing water-quality records.
///
///         It is not a tradeable asset. There is no balance to move, no transfer
///         or approval function, no supply, and no price, so no market can form
///         around it.
///
///         It has no issuer or admin of its own. A contributor credits
///         themselves, and this contract accepts a record only if the registry
///         attributes it to that same address, so it can neither grant nor
///         withhold recognition. Note the limit of that claim: the registry's
///         owner decides who may anchor at all, so recognition still depends on
///         a key held elsewhere.
///
///         What it proves is narrow: this address anchored these records. It says
///         nothing about whether the underlying measurements are accurate, and it
///         must not be read as a quality or trust rating.
contract VolunteerCredential {
    IWaterAuditRegistry public immutable registry;

    mapping(address => uint32) private contributionCounts;
    mapping(bytes32 => bool) private creditedRecords;

    event ContributionCredited(
        address indexed volunteer,
        bytes32 indexed recordHash,
        uint32 contributionCount
    );

    constructor(address registryAddress) {
        require(registryAddress != address(0), "registry address required");
        registry = IWaterAuditRegistry(registryAddress);
    }

    /// @notice Credit the caller for one record anchored on their behalf.
    /// @dev Reads `attributedTo`, not `submitter`, so a contributor is credited
    ///      whether they anchored the record themselves or a relayer did it for
    ///      them after verifying their signature.
    ///
    ///      Restricted to the caller on purpose. Claiming is a second, separate
    ///      decision from contributing, so nobody is enrolled here by someone else.
    function claimContribution(bytes32 recordHash) external {
        require(!creditedRecords[recordHash], "record already credited");

        IWaterAuditRegistry.Anchor memory anchor = registry.getAnchor(recordHash);
        require(anchor.anchoredAt != 0, "record is not anchored");
        require(anchor.attributedTo == msg.sender, "record is attributed to another address");

        creditedRecords[recordHash] = true;
        uint32 updatedCount = contributionCounts[msg.sender] + 1;
        contributionCounts[msg.sender] = updatedCount;

        emit ContributionCredited(msg.sender, recordHash, updatedCount);
    }

    function contributionCount(address volunteer) external view returns (uint32) {
        return contributionCounts[volunteer];
    }

    function isCredited(bytes32 recordHash) external view returns (bool) {
        return creditedRecords[recordHash];
    }
}
