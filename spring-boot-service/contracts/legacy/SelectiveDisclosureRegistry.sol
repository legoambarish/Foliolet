// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/// Commitments only. The operator is the custodial platform, not an issuer.
contract SelectiveDisclosureRegistry {
    address public immutable operator;
    struct CredentialAnchor {
        bytes32 merkleRoot;
        bytes32 documentCommitment;
        bytes32 provenanceDigest;
        address owner;
        uint64 anchoredAt;
        uint32 version;
        uint8 provenanceLevel;
        uint8 status; // 0 absent, 1 active, 2 revoked, 3 superseded
        bytes32 supersededBy;
    }
    mapping(bytes32 => CredentialAnchor) private credentials;
    event CredentialAnchored(bytes32 indexed credentialId, bytes32 merkleRoot, uint32 version);
    event CredentialRevoked(bytes32 indexed credentialId);
    event CredentialSuperseded(bytes32 indexed credentialId, bytes32 replacement);
    constructor() { operator = msg.sender; }
    modifier onlyOperator() { require(msg.sender == operator, "Only operator"); _; }

    function registerCredential(bytes32 id, bytes32 root, bytes32 documentCommitment,
        bytes32 provenanceDigest, uint32 version, uint8 provenanceLevel, bytes32 previous) external onlyOperator {
        require(id != bytes32(0) && root != bytes32(0) && documentCommitment != bytes32(0), "Empty commitment");
        require(credentials[id].status == 0, "Already anchored");
        require(provenanceLevel <= 1, "Unsupported assurance"); // 0 self, 1 authenticated first-seen
        if (previous == bytes32(0)) require(version == 1, "Initial version must be one");
        else {
            CredentialAnchor storage old = credentials[previous];
            require(old.status == 1 && version == old.version + 1, "Previous version unavailable");
            old.status = 3; old.supersededBy = id;
            emit CredentialSuperseded(previous, id);
        }
        credentials[id] = CredentialAnchor(root, documentCommitment, provenanceDigest, msg.sender,
            uint64(block.timestamp), version, provenanceLevel, 1, bytes32(0));
        emit CredentialAnchored(id, root, version);
    }
    function revokeCredential(bytes32 id) external onlyOperator {
        require(credentials[id].status == 1, "Credential not active");
        credentials[id].status = 2; emit CredentialRevoked(id);
    }
    function getCredential(bytes32 id) external view returns
        (bytes32, bytes32, bytes32, address, uint64, uint32, uint8, uint8, bytes32) {
        CredentialAnchor memory c = credentials[id];
        return (c.merkleRoot, c.documentCommitment, c.provenanceDigest, c.owner, c.anchoredAt,
            c.version, c.provenanceLevel, c.status, c.supersededBy);
    }
}
