// SPDX-License-Identifier: MIT
pragma solidity 0.8.19;

/// Local governance is a trust root, not proof of a real institution's identity.
contract EvidenceBridgeRegistry {
    address public immutable governance;
    struct Issuer { string name; bool recognized; bool suspended; uint64 changedBlock; }
    struct Evidence {
        bytes32 root; bytes32 documentCommitment; bytes32 claimType;
        address issuer; address holder; uint32 leafCount; uint32 version;
        uint64 issuedAt; uint64 expiresAt; uint64 anchorBlock; uint64 changedBlock;
        uint8 evidenceClass; uint8 status; bytes32 supersededBy;
    }
    mapping(address => Issuer) public issuers;
    mapping(address => mapping(bytes32 => bool)) public scopes;
    mapping(bytes32 => Evidence) private records;
    event IssuerRecognized(address indexed issuer, string name);
    event ScopeChanged(address indexed issuer, bytes32 indexed claimType, bool allowed);
    event IssuerSuspensionChanged(address indexed issuer, bool suspended);
    event Anchored(bytes32 indexed id, address indexed issuer, address indexed holder, bytes32 root);
    event Revoked(bytes32 indexed id);
    event Superseded(bytes32 indexed previous, bytes32 indexed replacement);
    constructor(address root) { require(root != address(0), "zero governance"); governance = root; }
    modifier onlyGovernance() { require(msg.sender == governance, "governance only"); _; }
    function recognize(address issuer, string calldata name, bytes32 claimType) external onlyGovernance {
        require(issuer != address(0) && bytes(name).length > 0 && bytes(name).length <= 120, "invalid issuer");
        require(!issuers[issuer].recognized, "already recognized");
        issuers[issuer] = Issuer(name, true, false, uint64(block.number)); scopes[issuer][claimType] = true;
        emit IssuerRecognized(issuer, name); emit ScopeChanged(issuer, claimType, true);
    }
    function setScope(address issuer, bytes32 claimType, bool allowed) external onlyGovernance {
        require(issuers[issuer].recognized, "unknown issuer");
        scopes[issuer][claimType] = allowed; issuers[issuer].changedBlock = uint64(block.number);
        emit ScopeChanged(issuer, claimType, allowed);
    }
    function suspend(address issuer, bool suspended) external onlyGovernance {
        require(issuers[issuer].recognized, "unknown issuer");
        issuers[issuer].suspended = suspended; issuers[issuer].changedBlock = uint64(block.number);
        emit IssuerSuspensionChanged(issuer, suspended);
    }
    function anchor(bytes32 id, bytes32 root, bytes32 documentCommitment, bytes32 claimType,
                    address holder, uint32 leafCount, uint32 version, uint64 expiresAt,
                    uint8 evidenceClass, bytes32 previous) external {
        Issuer memory issuer = issuers[msg.sender];
        require(issuer.recognized && !issuer.suspended && scopes[msg.sender][claimType], "issuer outside scope");
        require(evidenceClass == 2, "unsupported evidence class");
        require(id != bytes32(0) && records[id].status == 0 && root != bytes32(0) && documentCommitment != bytes32(0), "immutable id");
        require(holder != address(0) && leafCount > 0 && leafCount <= 128 && expiresAt > block.timestamp, "invalid evidence");
        if (previous == bytes32(0)) require(version == 1, "first version");
        else {
            Evidence storage old = records[previous];
            require(old.status == 1 && old.issuer == msg.sender && old.holder == holder && old.claimType == claimType && version == old.version + 1, "invalid replacement");
            old.status = 3; old.supersededBy = id; old.changedBlock = uint64(block.number); emit Superseded(previous, id);
        }
        records[id] = Evidence(root, documentCommitment, claimType, msg.sender, holder, leafCount, version,
                              uint64(block.timestamp), expiresAt, uint64(block.number), uint64(block.number), evidenceClass, 1, bytes32(0));
        emit Anchored(id, msg.sender, holder, root);
    }
    function revoke(bytes32 id) external {
        Evidence storage record = records[id];
        require(record.issuer == msg.sender && record.status == 1, "own active evidence only");
        record.status = 2; record.changedBlock = uint64(block.number); emit Revoked(id);
    }
    function getEvidence(bytes32 id) external view returns (Evidence memory) { return records[id]; }
    /// Effective state is read-time policy. Stored roots and irreversible lifecycle are unchanged.
    /// 0 missing, 1 active, 2 revoked, 3 superseded, 4 expired, 5 issuer authority inactive.
    function getCredential(bytes32 id) external view returns (Evidence memory record, uint8 effectiveStatus, uint64 lastChangeBlock) {
        record = records[id]; effectiveStatus = record.status;
        Issuer memory issuer = issuers[record.issuer];
        lastChangeBlock = record.changedBlock > issuer.changedBlock ? record.changedBlock : issuer.changedBlock;
        if (effectiveStatus == 1) {
            if (record.expiresAt <= block.timestamp) effectiveStatus = 4;
            else if (!issuer.recognized || issuer.suspended || !scopes[record.issuer][record.claimType]) effectiveStatus = 5;
        }
    }
}
